import asyncio
import logging
import time
from dataclasses import dataclass

from config import Settings
from okx_client import OKXClient
from state import BotState, PositionState, StateStore


@dataclass(frozen=True)
class TradeSignal:
    inst_id: str
    entry_price: float | None
    stop_loss: float
    stop_loss_is_candle_close: bool
    tp1: float


class TradingBot:
    def __init__(self, settings: Settings, okx_client: OKXClient, state_store: StateStore) -> None:
        self.settings = settings
        self.okx_client = okx_client
        self.state_store = state_store
        self.state = state_store.load()
        self._monitor_tasks: dict[str, asyncio.Task[None]] = {}

    async def handle_signal(self, signal: TradeSignal) -> None:
        if len(self.state.positions) >= self.settings.max_open_positions:
            logging.warning("Max open positions reached; ignoring new signal.")
            return
        if signal.inst_id in self.state.positions:
            logging.warning("Position already open for %s; ignoring signal.", signal.inst_id)
            return

        try:
            current_price = await asyncio.to_thread(self.okx_client.get_ticker, signal.inst_id)
            balance = await asyncio.to_thread(self.okx_client.get_balance, self.settings.base_currency)
        except Exception as exc:
            logging.error("Failed to fetch price or balance: %s", exc)
            return

        allocation = balance / self.settings.max_open_positions
        if allocation <= 0:
            logging.error("No available balance to open a new trade.")
            return

        size = allocation / current_price
        try:
            await asyncio.to_thread(self.okx_client.place_market_order, signal.inst_id, "buy", size)
        except Exception as exc:
            logging.error("Failed to place entry order: %s", exc)
            return

        stop_order_id = None
        if not signal.stop_loss_is_candle_close:
            try:
                stop_order_id = await asyncio.to_thread(
                    self.okx_client.place_stop_loss_order,
                    signal.inst_id,
                    "sell",
                    signal.stop_loss,
                    size,
                )
            except Exception as exc:
                logging.warning("Failed to place stop loss order; bot will monitor manually. %s", exc)

        position = PositionState(
            symbol=signal.inst_id,
            size=size,
            entry_price=current_price,
            stop_loss=signal.stop_loss,
            stop_loss_is_candle_close=signal.stop_loss_is_candle_close,
            tp1=signal.tp1,
            stop_order_id=stop_order_id,
        )
        self.state.positions[signal.inst_id] = position
        self.state_store.save(self.state)

        task = asyncio.create_task(self._monitor_position(signal.inst_id))
        self._monitor_tasks[signal.inst_id] = task

    async def _monitor_position(self, inst_id: str) -> None:
        logging.info("Monitoring position %s", inst_id)
        while inst_id in self.state.positions:
            position = self.state.positions[inst_id]
            try:
                price = await asyncio.to_thread(self.okx_client.get_ticker, inst_id)
            except Exception as exc:
                logging.warning("Price check failed for %s: %s", inst_id, exc)
                await asyncio.sleep(self.settings.poll_interval_seconds)
                continue

            if not position.trailing_active and price >= position.tp1:
                await self._activate_trailing(position, price)

            if position.trailing_active:
                await self._update_trailing(position, price)
            elif position.stop_loss and price <= position.stop_loss:
                logging.info("Stop loss price hit for %s. Closing position.", position.symbol)
                await self._close_position(position)
                continue

            if position.stop_loss_is_candle_close:
                now = time.time()
                if (
                    position.last_candle_check is None
                    or now - position.last_candle_check >= self.settings.candle_check_interval_seconds
                ):
                    position.last_candle_check = now
                    await self._check_candle_stop(position)

            await asyncio.sleep(self.settings.poll_interval_seconds)

    async def _activate_trailing(self, position: PositionState, price: float) -> None:
        logging.info("TP1 reached for %s. Activating trailing stop.", position.symbol)
        if position.stop_order_id:
            try:
                await asyncio.to_thread(self.okx_client.cancel_algo_order, position.stop_order_id, position.symbol)
            except Exception as exc:
                logging.warning("Failed to cancel stop order: %s", exc)
        position.trailing_active = True
        position.highest_price = price
        position.trailing_stop = price * (1 - self.settings.trailing_percent)
        self.state_store.save(self.state)

    async def _update_trailing(self, position: PositionState, price: float) -> None:
        if position.highest_price is None or position.trailing_stop is None:
            return
        if price > position.highest_price:
            position.highest_price = price
            position.trailing_stop = price * (1 - self.settings.trailing_percent)
            logging.info("Trailing stop updated for %s to %.6f", position.symbol, position.trailing_stop)
            self.state_store.save(self.state)
            return

        if price <= position.trailing_stop:
            logging.info("Trailing stop hit for %s. Closing position.", position.symbol)
            await self._close_position(position)

    async def _check_candle_stop(self, position: PositionState) -> None:
        try:
            candles = await asyncio.to_thread(self.okx_client.get_candles, position.symbol, "4H", 2)
        except Exception as exc:
            logging.warning("Candle check failed for %s: %s", position.symbol, exc)
            return
        latest = candles[0]
        close_price = float(latest[4])
        if close_price < position.stop_loss:
            logging.info("4H close below stop for %s. Closing position.", position.symbol)
            await self._close_position(position)

    async def _close_position(self, position: PositionState) -> None:
        if position.stop_order_id:
            try:
                await asyncio.to_thread(self.okx_client.cancel_algo_order, position.stop_order_id, position.symbol)
            except Exception as exc:
                logging.warning("Failed to cancel stop order for %s: %s", position.symbol, exc)
        try:
            await asyncio.to_thread(self.okx_client.place_market_order, position.symbol, "sell", position.size)
        except Exception as exc:
            logging.error("Failed to close position %s: %s", position.symbol, exc)
            return
        self.state.positions.pop(position.symbol, None)
        self.state_store.save(self.state)
