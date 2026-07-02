from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import ssl
from datetime import datetime, timezone
from typing import Any

from aiogram import Bot, html
from aiohttp import ClientConnectorCertificateError, ClientError
from bot.config import Config
from bot.storage.repository import ShopRepository
from bot.utils.formatting import format_money
from bot.utils.i18n import tr
from bot.utils.premium_emoji import category_premium_emoji, premium_emoji

from .cryptobot_client import CryptoBotApiError, CryptoBotClient


logger = logging.getLogger(__name__)


class CryptoBotPaymentService:
    def __init__(
        self,
        *,
        repo: ShopRepository,
        config: Config,
        client: CryptoBotClient,
        bot: Bot,
    ) -> None:
        self.repo = repo
        self.config = config
        self.client = client
        self.bot = bot
        self._sync_task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()

    def is_enabled(self) -> bool:
        return self.config.cryptopay_enabled

    def build_success_url(self, payment_id: int) -> str:
        if not self.config.public_base_url:
            return "https://t.me/"
        return f"{self.config.public_base_url}/payments/cryptobot/success?payment_id={payment_id}"

    def build_webhook_url(self) -> str | None:
        if not self.config.public_base_url or not self.config.cryptopay_webhook_path_token:
            return None
        return (
            f"{self.config.public_base_url}/payments/cryptobot/webhook/"
            f"{self.config.cryptopay_webhook_path_token}"
        )

    def verify_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:
        if not signature or not self.config.cryptopay_api_token:
            return False
        secret = hashlib.sha256(self.config.cryptopay_api_token.encode("utf-8")).digest()
        digest = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, signature)

    def validate_webhook_freshness(self, request_date: str | None) -> bool:
        if not request_date:
            return False
        try:
            request_dt = datetime.fromisoformat(request_date.replace("Z", "+00:00"))
        except ValueError:
            return False
        now = datetime.now(timezone.utc)
        age = abs((now - request_dt.astimezone(timezone.utc)).total_seconds())
        return age <= max(self.config.cryptopay_webhook_max_age_seconds, 0)

    async def create_deposit_invoice(self, tg_user_id: int, amount_cents: int) -> dict[str, Any]:
        user = await self.repo.get_user_by_tg_id(tg_user_id)
        if not user:
            raise ValueError(tr("ru", "user_not_found"))
        payment = await self.repo.create_crypto_payment(
            user_id=user["id"],
            amount_cents=amount_cents,
            currency=self.config.cryptopay_invoice_currency,
            purpose="deposit",
            lifetime_seconds=self.config.cryptopay_invoice_lifetime,
        )
        return await self._create_and_attach_invoice(payment, user=user)

    async def create_product_invoice(self, tg_user_id: int, product_id: int) -> dict[str, Any]:
        user = await self.repo.get_user_by_tg_id(tg_user_id)
        if not user:
            raise ValueError(tr("ru", "user_not_found"))
        payment = await self.repo.create_crypto_payment(
            user_id=user["id"],
            amount_cents=0,
            currency=self.config.cryptopay_invoice_currency,
            purpose="product_purchase",
            product_id=product_id,
            lifetime_seconds=self.config.cryptopay_invoice_lifetime,
        )
        return await self._create_and_attach_invoice(payment, user=user)

    async def sync_payment_for_user(self, tg_user_id: int, payment_id: int) -> dict[str, Any]:
        payment = await self.repo.get_user_payment_by_id(tg_user_id, payment_id)
        if not payment:
            raise ValueError(tr("ru", "payment_not_found"))
        if payment["status"] == "completed":
            return payment
        provider_invoice_id = payment.get("provider_invoice_id")
        if not provider_invoice_id:
            return payment
        try:
            invoice = await self.client.get_invoice(invoice_id=int(provider_invoice_id))
        except Exception as exc:
            raise ValueError(self._public_error_message(exc, payment.get("language_code"))) from exc
        result = await self.repo.apply_crypto_invoice(invoice)
        await self._notify_on_state_change(result)
        refreshed = await self.repo.get_user_payment_by_id(tg_user_id, payment_id)
        return refreshed or payment

    async def process_webhook(
        self,
        payload: dict[str, Any],
        *,
        signature: str | None,
        raw_body: bytes,
    ) -> dict[str, Any]:
        if not self.verify_webhook_signature(raw_body, signature):
            raise PermissionError("Invalid Crypto Pay signature")
        if not self.validate_webhook_freshness(payload.get("request_date")):
            raise PermissionError("Stale Crypto Pay webhook")
        if payload.get("update_type") != "invoice_paid":
            return {"action": "ignored"}
        invoice = payload.get("payload")
        if not isinstance(invoice, dict):
            raise ValueError("Webhook payload is missing invoice object")
        result = await self.repo.apply_crypto_invoice(invoice)
        await self._notify_on_state_change(result)
        return result

    async def start_background_sync(self) -> None:
        if not self.is_enabled() or self._sync_task is not None:
            return
        self._stopped.clear()
        self._sync_task = asyncio.create_task(self._background_sync_loop())

    async def stop_background_sync(self) -> None:
        self._stopped.set()
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            self._sync_task = None

    async def _background_sync_loop(self) -> None:
        try:
            while not self._stopped.is_set():
                await self.repo.release_expired_reservations()
                payments = await self.repo.list_pending_crypto_payments(limit=50)
                invoice_ids = [int(payment["provider_invoice_id"]) for payment in payments if payment.get("provider_invoice_id")]
                if invoice_ids:
                    try:
                        invoices = await self.client.get_invoices(invoice_ids=invoice_ids)
                        invoices_by_id = {
                            int(invoice["invoice_id"]): invoice
                            for invoice in invoices
                            if invoice.get("invoice_id") is not None
                        }
                        for payment in payments:
                            invoice_id = payment.get("provider_invoice_id")
                            if not invoice_id:
                                continue
                            invoice = invoices_by_id.get(int(invoice_id))
                            if invoice is None:
                                await self.repo.mark_payment_expired_if_due(payment["id"])
                                continue
                            result = await self.repo.apply_crypto_invoice(invoice)
                            await self._notify_on_state_change(result)
                    except Exception:
                        logger.exception("Failed to sync CryptoBot payments")
                try:
                    await asyncio.wait_for(
                        self._stopped.wait(),
                        timeout=max(self.config.cryptopay_sync_interval_seconds, 15),
                    )
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise

    async def _create_and_attach_invoice(self, payment: dict[str, Any], *, user: dict[str, Any]) -> dict[str, Any]:
        if not self.is_enabled():
            raise ValueError(tr(user.get("language_code"), "cryptopay_not_configured"))
        payload = {
            "currency_type": "fiat",
            "fiat": self.config.cryptopay_invoice_currency,
            "amount": self.client.cents_to_amount(payment["amount_cents"]),
            "description": await self._build_description(payment, user.get("language_code")),
            "payload": json.dumps(
                {
                    "payment_db_id": payment["id"],
                    "payment_ref": payment["provider_payment_id"],
                    "purpose": payment["purpose"],
                    "product_id": payment.get("product_id"),
                    "tg_user_id": user["tg_id"],
                },
                ensure_ascii=True,
                separators=(",", ":"),
            ),
            "allow_comments": self.config.cryptopay_allow_comments,
            "allow_anonymous": self.config.cryptopay_allow_anonymous,
            "expires_in": self.config.cryptopay_invoice_lifetime,
        }
        if self.config.cryptopay_accepted_assets:
            payload["accepted_assets"] = ",".join(self.config.cryptopay_accepted_assets)
        hidden_message = await self._build_hidden_message(payment, user.get("language_code"))
        if hidden_message:
            payload["hidden_message"] = hidden_message
        success_url = self.build_success_url(payment["id"])
        if success_url:
            payload["paid_btn_name"] = "callback"
            payload["paid_btn_url"] = success_url
        try:
            invoice = await self.client.create_invoice(payload)
        except Exception as exc:
            await self.repo.mark_payment_failed(payment["id"], str(exc), release_reservation=True)
            raise ValueError(self._public_error_message(exc, user.get("language_code"))) from exc
        updated = await self.repo.attach_crypto_invoice(payment["id"], invoice)
        return updated

    async def _build_description(self, payment: dict[str, Any], language_code: str | None) -> str:
        lang = language_code
        if payment["purpose"] == "deposit":
            return tr(lang, "crypto_deposit_description")
        product = await self.repo.get_product(payment["product_id"])
        localized_product = self.repo.localize_product(product, lang) if product else None
        product_name = localized_product["title"] if localized_product else tr(lang, "shop_product_fallback")
        return tr(lang, "crypto_product_description", product_name=product_name)

    async def _build_hidden_message(self, payment: dict[str, Any], language_code: str | None) -> str | None:
        lang = language_code
        if payment["purpose"] == "deposit":
            return tr(lang, "crypto_deposit_hidden_message")
        return tr(lang, "crypto_product_hidden_message")

    async def _notify_on_state_change(self, result: dict[str, Any]) -> None:
        action = result.get("action")
        if action not in {"completed", "paid_unfulfilled"}:
            return
        payment = result.get("payment") or {}
        user = result.get("user") or {}
        if not user.get("tg_id"):
            return
        lang = user.get("language_code")
        if action == "paid_unfulfilled":
            await self.bot.send_message(
                user["tg_id"],
                tr(
                    lang,
                    "payment_fulfillment_issue",
                    important_emoji=premium_emoji("important"),
                    payment_id=payment.get("id", "—"),
                ),
            )
            return
        if payment.get("purpose") == "deposit":
            text = tr(
                lang,
                "balance_topped_up",
                balance_emoji=premium_emoji("balance"),
                amount=format_money(payment["amount_cents"]),
                balance=format_money(user["balance_cents"]),
            )
            await self.bot.send_message(user["tg_id"], text)
            return
        order = result.get("order") or {}
        icon = category_premium_emoji(order)
        text = tr(
            lang,
            "payment_success_notified",
            order_emoji=premium_emoji("order"),
            category_emoji=icon,
            product_title=html.quote(self.repo.localize_product_title(order, lang) or tr(lang, "shop_product_fallback")),
            price_emoji=premium_emoji("price"),
            amount=format_money(order.get("amount_cents", 0)),
            key_value=html.quote(order.get("key_value", "—")),
        )
        await self.bot.send_message(user["tg_id"], text)

    @staticmethod
    def _public_error_message(exc: Exception, language_code: str | None = "ru") -> str:
        if isinstance(exc, (ClientConnectorCertificateError, ssl.SSLCertVerificationError)):
            return tr(language_code, "secure_connection_error")
        if isinstance(exc, (ClientError, TimeoutError)):
            return tr(language_code, "gateway_unavailable")
        if isinstance(exc, CryptoBotApiError):
            message = str(exc)
            if len(message) > 180:
                return tr(language_code, "invoice_create_failed")
            return message
        message = str(exc).strip()
        if not message or len(message) > 180:
            return tr(language_code, "invoice_create_failed")
        return message
