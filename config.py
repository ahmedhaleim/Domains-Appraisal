from dataclasses import dataclass
import os


class MissingConfigError(ValueError):
    def __init__(self, missing: list[str]) -> None:
        message = "Missing required environment variables: " + ", ".join(missing)
        super().__init__(message)
        self.missing = missing


@dataclass(frozen=True)
class Settings:
    okx_api_key: str
    okx_api_secret: str
    okx_api_passphrase: str
    okx_base_url: str
    telegram_api_id: int
    telegram_api_hash: str
    telegram_session: str
    telegram_group_ids: list[int]
    base_currency: str
    max_open_positions: int
    trailing_percent: float
    poll_interval_seconds: int
    candle_check_interval_seconds: int
    state_file: str


def _split_group_ids(raw: str) -> list[int]:
    return [int(value.strip()) for value in raw.split(",") if value.strip()]


def load_settings() -> Settings:
    okx_api_key = os.environ.get("OKX_API_KEY", "").strip()
    okx_api_secret = os.environ.get("OKX_API_SECRET", "").strip()
    okx_api_passphrase = os.environ.get("OKX_API_PASSPHRASE", "").strip()
    okx_base_url = os.environ.get("OKX_BASE_URL", "https://www.okx.com").strip()

    telegram_api_id = os.environ.get("TELEGRAM_API_ID", "").strip()
    telegram_api_hash = os.environ.get("TELEGRAM_API_HASH", "").strip()
    telegram_session = os.environ.get("TELEGRAM_SESSION", "").strip()
    telegram_group_ids = _split_group_ids(os.environ.get("TELEGRAM_GROUP_IDS", "").strip())

    missing: list[str] = []
    if not okx_api_key:
        missing.append("OKX_API_KEY")
    if not okx_api_secret:
        missing.append("OKX_API_SECRET")
    if not okx_api_passphrase:
        missing.append("OKX_API_PASSPHRASE")
    if not telegram_api_id:
        missing.append("TELEGRAM_API_ID")
    if not telegram_api_hash:
        missing.append("TELEGRAM_API_HASH")
    if not telegram_session:
        missing.append("TELEGRAM_SESSION")
    if not telegram_group_ids:
        missing.append("TELEGRAM_GROUP_IDS")
    if missing:
        raise MissingConfigError(missing)

    return Settings(
        okx_api_key=okx_api_key,
        okx_api_secret=okx_api_secret,
        okx_api_passphrase=okx_api_passphrase,
        okx_base_url=okx_base_url,
        telegram_api_id=int(telegram_api_id),
        telegram_api_hash=telegram_api_hash,
        telegram_session=telegram_session,
        telegram_group_ids=telegram_group_ids,
        base_currency=os.environ.get("BASE_CURRENCY", "USDT").strip().upper(),
        max_open_positions=int(os.environ.get("MAX_OPEN_POSITIONS", "4")),
        trailing_percent=float(os.environ.get("TRAILING_PERCENT", "0.02")),
        poll_interval_seconds=int(os.environ.get("POLL_INTERVAL_SECONDS", "10")),
        candle_check_interval_seconds=int(os.environ.get("CANDLE_CHECK_INTERVAL_SECONDS", "60")),
        state_file=os.environ.get("STATE_FILE", "state.json"),
    )
