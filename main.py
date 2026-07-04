import asyncio
import logging
import ssl

import certifi
from aiohttp import ClientSession, ClientTimeout, TCPConnector, web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import load_config
from bot.handlers import admin, user
from bot.services.cryptobot_client import CryptoBotClient
from bot.services.lolzteam_client import LolzteamClient
from bot.services.payment_web import create_payment_app
from bot.services.payments import CryptoBotPaymentService, LolzteamPaymentService, PaymentService, PlategaPaymentService
from bot.services.platega_client import PlategaClient
from bot.storage.repository import ShopRepository


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    config = load_config()
    repo = ShopRepository(config.database_path)
    await repo.initialize(config)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    http_session = ClientSession(
        timeout=ClientTimeout(total=20),
        connector=TCPConnector(ssl=ssl_context),
    )
    cryptobot_client = CryptoBotClient(http_session, config.cryptopay_api_base, config.cryptopay_api_token)
    lolzteam_client = LolzteamClient(http_session, config.lolz_api_base, config.lolz_api_token)
    platega_client = PlategaClient(
        http_session,
        config.platega_api_base,
        config.platega_merchant_id,
        config.platega_secret,
        create_path=config.platega_create_path,
        create_path_fallback=config.platega_create_path_fallback,
    )
    cryptobot_service = CryptoBotPaymentService(repo=repo, config=config, client=cryptobot_client, bot=bot)
    lolzteam_service = LolzteamPaymentService(repo=repo, config=config, client=lolzteam_client, bot=bot)
    platega_service = PlategaPaymentService(repo=repo, config=config, client=platega_client, bot=bot)
    payment_service = PaymentService(repo=repo, cryptobot=cryptobot_service, lolzteam=lolzteam_service, platega=platega_service)
    dp = Dispatcher()
    dp["config"] = config
    dp["repo"] = repo
    dp["payment_service"] = payment_service

    dp.include_router(user.router)
    dp.include_router(admin.router)

    app = create_payment_app(payment_service, cryptobot_service, lolzteam_service, platega_service, repo, config)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=config.app_host, port=config.app_port)
    await site.start()
    await payment_service.start_background_sync()

    try:
        await dp.start_polling(bot)
    finally:
        await payment_service.stop_background_sync()
        await runner.cleanup()
        await http_session.close()
        await repo.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
