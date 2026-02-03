import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class PositionState:
    symbol: str
    size: float
    entry_price: float
    stop_loss: float | None
    stop_loss_is_candle_close: bool
    tp1: float
    stop_order_id: str | None = None
    trailing_active: bool = False
    trailing_stop: float | None = None
    highest_price: float | None = None
    last_candle_check: float | None = None


@dataclass
class BotState:
    positions: dict[str, PositionState] = field(default_factory=dict)


class StateStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def load(self) -> BotState:
        if not self.path.exists():
            return BotState()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        positions = {
            symbol: PositionState(**payload) for symbol, payload in raw.get("positions", {}).items()
        }
        return BotState(positions=positions)

    def save(self, state: BotState) -> None:
        payload = {
            "positions": {symbol: asdict(position) for symbol, position in state.positions.items()}
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
