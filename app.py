import asyncio
import logging

from config import MissingConfigError, load_settings
from okx_client import OKXClient
from state import StateStore
from strategy import TradingBot
from telegram_listener import build_telegram_client


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


async def main() -> None:
    try:
        settings = load_settings()
    except MissingConfigError as exc:
        logging.error("%s", exc)
        logging.info("Set the missing variables in Railway, then restart the service.")
        return
    okx_client = OKXClient(
        api_key=settings.okx_api_key,
        api_secret=settings.okx_api_secret,
        passphrase=settings.okx_api_passphrase,
        base_url=settings.okx_base_url,
    )
    state_store = StateStore(settings.state_file)
    bot = TradingBot(settings=settings, okx_client=okx_client, state_store=state_store)

    telegram_client = build_telegram_client(settings, bot)
    await telegram_client.start()
    logging.info("Telegram listener started. Waiting for signals...")
    await telegram_client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
