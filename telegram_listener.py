import logging
import re

from telethon import TelegramClient, events
from telethon.sessions import StringSession

from config import Settings
from strategy import TradeSignal, TradingBot


SIGNAL_PATTERN = re.compile(
    r"(?P<side>buy|sell)\s+"
    r"(?P<symbol>[A-Z0-9]+[/\-]?[A-Z0-9]+)\s+"
    r"(?:entry\s*(?P<entry>[0-9.]+)\s+)?"
    r"(?:sl\s*(?P<sl>[0-9.]+)\s*(?P<sl_cond>4h)?\s*)?"
    r"(?:tp1\s*(?P<tp1>[0-9.]+))?",
    re.IGNORECASE,
)


def parse_signal(message: str) -> TradeSignal | None:
    match = SIGNAL_PATTERN.search(message.replace("\n", " "))
    if not match:
        return None
    side = match.group("side").lower()
    raw_symbol = match.group("symbol").upper().replace("-", "/")
    symbol = raw_symbol.replace("/", "-")
    entry = float(match.group("entry")) if match.group("entry") else None
    stop_loss = float(match.group("sl")) if match.group("sl") else None
    stop_loss_is_candle = bool(match.group("sl_cond"))
    tp1 = float(match.group("tp1")) if match.group("tp1") else None

    if side != "buy":
        return None
    if not stop_loss or not tp1:
        return None
    return TradeSignal(
        inst_id=f"{symbol}",
        entry_price=entry,
        stop_loss=stop_loss,
        stop_loss_is_candle_close=stop_loss_is_candle,
        tp1=tp1,
    )


def build_telegram_client(settings: Settings, bot: TradingBot) -> TelegramClient:
    client = TelegramClient(
        StringSession(settings.telegram_session),
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )

    @client.on(events.NewMessage(chats=settings.telegram_group_ids))
    async def handle_message(event: events.NewMessage.Event) -> None:
        message = event.message.message or ""
        signal = parse_signal(message)
        if not signal:
            return
        logging.info("Signal received: %s", signal)
        await bot.handle_signal(signal)

    return client
