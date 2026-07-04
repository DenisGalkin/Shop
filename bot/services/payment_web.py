from __future__ import annotations

import html
import json
import logging
from typing import Any

from aiohttp import web

from bot.config import Config
from bot.storage.repository import ShopRepository

from .admin_web import setup_admin_routes
from .payments import (
    CryptoBotPaymentService,
    HeleketPaymentService,
    LolzteamPaymentService,
    PaymentService,
    PlategaPaymentService,
)


logger = logging.getLogger(__name__)


async def cryptobot_webhook(request: web.Request) -> web.Response:
    service: CryptoBotPaymentService = request.app["cryptobot_service"]
    signature = request.headers.get("crypto-pay-api-signature")
    raw_body = await request.read()
    try:
        payload: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        await service.process_webhook(payload, signature=signature, raw_body=raw_body)
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


async def heleket_webhook(request: web.Request) -> web.Response:
    service: HeleketPaymentService = request.app["heleket_service"]
    raw_body = await request.read()
    try:
        payload: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        await service.process_webhook(payload)
    except PermissionError:
        logger.warning("Rejected Heleket webhook due to invalid signature")
        raise web.HTTPForbidden(text="forbidden")
    except ValueError:
        logger.exception("Rejected malformed Heleket webhook payload")
        raise web.HTTPBadRequest(text="bad request")
    except Exception:
        logger.exception("Heleket webhook processing failed")
        raise web.HTTPInternalServerError(text="error")
    return web.json_response({"ok": True})


async def lolzteam_webhook(request: web.Request) -> web.Response:
    service: LolzteamPaymentService = request.app["lolzteam_service"]
    secret = request.headers.get("x-secret-key")
    raw_body = await request.read()
    try:
        payload: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        await service.process_webhook(payload, secret=secret)
    except PermissionError:
        logger.warning("Rejected Lolzteam webhook due to invalid x-secret-key")
        raise web.HTTPForbidden(text="forbidden")
    except ValueError:
        logger.exception("Rejected malformed Lolzteam webhook payload")
        raise web.HTTPBadRequest(text="bad request")
    except Exception:
        logger.exception("Lolzteam webhook processing failed")
        raise web.HTTPInternalServerError(text="error")
    return web.json_response({"ok": True})


async def platega_webhook(request: web.Request) -> web.Response:
    service: PlategaPaymentService = request.app["platega_service"]
    merchant_id = request.headers.get("X-MerchantId")
    secret = request.headers.get("X-Secret")
    raw_body = await request.read()
    try:
        payload: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        await service.process_webhook(payload, merchant_id=merchant_id, secret=secret)
    except PermissionError:
        logger.warning("Rejected Platega webhook due to invalid X-MerchantId or X-Secret")
        raise web.HTTPForbidden(text="forbidden")
    except ValueError:
        logger.exception("Rejected malformed Platega webhook payload")
        raise web.HTTPBadRequest(text="bad request")
    except Exception:
        logger.exception("Platega webhook processing failed")
        raise web.HTTPInternalServerError(text="error")
    return web.json_response({"ok": True})


async def payment_success(request: web.Request) -> web.Response:
    payment_id = request.query.get("payment_id", "")
    safe_payment_id = html.escape(payment_id or "—", quote=True)
    html_text = (
        "<html><head><meta charset='utf-8'><title>Оплата принята</title></head>"
        "<body style='font-family: Arial, sans-serif; max-width: 720px; margin: 48px auto; line-height: 1.5;'>"
        "<h1>Оплата обрабатывается</h1>"
        "<p>Если платёж уже прошёл, бот скоро подтвердит пополнение или выдаст товар автоматически.</p>"
        f"<p>ID платежа: <code>{safe_payment_id}</code></p>"
        "<p>Вернитесь в Telegram и нажмите кнопку проверки статуса, если сообщение ещё не пришло.</p>"
        "</body></html>"
    )
    return web.Response(text=html_text, content_type="text/html")


def create_payment_app(
    service: PaymentService,
    heleket_service: HeleketPaymentService,
    cryptobot_service: CryptoBotPaymentService,
    lolzteam_service: LolzteamPaymentService,
    platega_service: PlategaPaymentService,
    repo: ShopRepository,
    config: Config,
) -> web.Application:
    app = web.Application()
    app["payment_service"] = service
    app["heleket_service"] = heleket_service
    app["cryptobot_service"] = cryptobot_service
    app["lolzteam_service"] = lolzteam_service
    app["platega_service"] = platega_service
    app["repo"] = repo
    app["config"] = config
    if config.heleket_webhook_path_token:
        app.router.add_post(
            f"/payments/heleket/webhook/{config.heleket_webhook_path_token}",
            heleket_webhook,
        )
    if config.cryptopay_webhook_path_token:
        app.router.add_post(
            f"/payments/cryptobot/webhook/{config.cryptopay_webhook_path_token}",
            cryptobot_webhook,
        )
    if config.lolz_webhook_path_token:
        app.router.add_post(
            f"/payments/lolzteam/callback/{config.lolz_webhook_path_token}",
            lolzteam_webhook,
        )
    if config.platega_webhook_path_token:
        app.router.add_post(
            f"/payments/platega/webhook/{config.platega_webhook_path_token}",
            platega_webhook,
        )
    app.router.add_get("/payments/heleket/success", payment_success)
    app.router.add_get("/payments/cryptobot/success", payment_success)
    app.router.add_get("/payments/lolzteam/success", payment_success)
    app.router.add_get("/payments/platega/success", payment_success)
    setup_admin_routes(app)
    return app
