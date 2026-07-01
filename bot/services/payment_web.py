from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import web

from bot.config import Config
from bot.storage.repository import ShopRepository

from .admin_web import setup_admin_routes
from .payments import CryptoBotPaymentService


logger = logging.getLogger(__name__)


async def cryptobot_webhook(request: web.Request) -> web.Response:
    service: CryptoBotPaymentService = request.app["payment_service"]
    signature = request.headers.get("crypto-pay-api-signature")
    raw_body = await request.read()
    try:
        payload: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        await service.process_webhook(
            payload,
            signature=signature,
            raw_body=raw_body,
        )
    except PermissionError:
        logger.warning("Rejected Crypto Pay webhook due to invalid signature or timestamp")
        raise web.HTTPForbidden(text="forbidden")
    except ValueError:
        logger.exception("Rejected malformed Crypto Pay webhook payload")
        raise web.HTTPBadRequest(text="bad request")
    except Exception:
        logger.exception("Crypto Pay webhook processing failed")
        raise web.HTTPInternalServerError(text="error")
    return web.json_response({"ok": True})


async def cryptobot_success(request: web.Request) -> web.Response:
    payment_id = request.query.get("payment_id", "")
    html_text = (
        "<html><head><meta charset='utf-8'><title>Оплата принята</title></head>"
        "<body style='font-family: Arial, sans-serif; max-width: 720px; margin: 48px auto; line-height: 1.5;'>"
        "<h1>Оплата обрабатывается</h1>"
        "<p>Если платёж уже прошёл, бот скоро подтвердит пополнение или выдаст товар автоматически.</p>"
        f"<p>ID платежа: <code>{payment_id or '—'}</code></p>"
        "<p>Вернитесь в Telegram и нажмите кнопку проверки статуса, если сообщение ещё не пришло.</p>"
        "</body></html>"
    )
    return web.Response(text=html_text, content_type="text/html")


def create_payment_app(service: CryptoBotPaymentService, repo: ShopRepository, config: Config) -> web.Application:
    app = web.Application()
    app["payment_service"] = service
    app["repo"] = repo
    app["config"] = config
    webhook_path = f"/payments/cryptobot/webhook/{service.config.cryptopay_webhook_path_token}"
    app.router.add_post(webhook_path, cryptobot_webhook)
    app.router.add_get("/payments/cryptobot/success", cryptobot_success)
    setup_admin_routes(app)
    return app
