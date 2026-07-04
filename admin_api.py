import logging

from aiohttp import web

from bot.config import load_config
from bot.services.admin_web import setup_admin_routes
from bot.storage.repository import ShopRepository


async def create_app() -> web.Application:
    config = load_config()
    repo = ShopRepository(config.database_path)
    await repo.initialize(config)

    app = web.Application()
    app["config"] = config
    app["repo"] = repo
    setup_admin_routes(app)

    async def close_repo(_: web.Application) -> None:
        await repo.close()

    app.on_cleanup.append(close_repo)
    return app


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    config = load_config()
    web.run_app(create_app(), host=config.app_host, port=config.app_port)


if __name__ == "__main__":
    main()
