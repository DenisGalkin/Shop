from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import ssl
from datetime import datetime, timezone
from typing import Any, Protocol

from aiogram import Bot, html
from aiohttp import ClientConnectorCertificateError, ClientError

from bot.config import Config
from bot.storage.repository import ShopRepository
from bot.utils.formatting import format_money
from bot.utils.i18n import tr
from bot.utils.premium_emoji import category_premium_emoji, premium_emoji

from .cryptobot_client import CryptoBotApiError, CryptoBotClient
from .lolzteam_client import LolzteamApiError, LolzteamClient


logger = logging.getLogger(__name__)


class PaymentProvider(Protocol):
    payment_type: str

    def is_enabled(self) -> bool: ...

    async def create_deposit_invoice(self, tg_user_id: int, amount_cents: int) -> dict[str, Any]: ...

    async def create_product_invoice(self, tg_user_id: int, product_id: int) -> dict[str, Any]: ...

    async def sync_payment(self, payment: dict[str, Any]) -> dict[str, Any]: ...

    async def start_background_sync(self) -> None: ...

    async def stop_background_sync(self) -> None: ...


class BasePaymentService:
    payment_type = ""

    def __init__(self, *, repo: ShopRepository, config: Config, bot: Bot) -> None:
        self.repo = repo
        self.config = config
        self.bot = bot
        self._sync_task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()

    async def create_deposit_invoice(self, tg_user_id: int, amount_cents: int) -> dict[str, Any]:
        user = await self.repo.get_user_by_tg_id(tg_user_id)
        if not user:
            raise ValueError(tr("ru", "user_not_found"))
        payment = await self._create_payment_record(
            user_id=user["id"],
            amount_cents=amount_cents,
            currency=self.invoice_currency(),
            purpose="deposit",
            lifetime_seconds=self.invoice_lifetime_seconds(),
        )
        return await self._create_and_attach_invoice(payment, user=user)

    async def create_product_invoice(self, tg_user_id: int, product_id: int) -> dict[str, Any]:
        user = await self.repo.get_user_by_tg_id(tg_user_id)
        if not user:
            raise ValueError(tr("ru", "user_not_found"))
        payment = await self._create_payment_record(
            user_id=user["id"],
            amount_cents=0,
            currency=self.invoice_currency(),
            purpose="product_purchase",
            product_id=product_id,
            lifetime_seconds=self.invoice_lifetime_seconds(),
        )
        return await self._create_and_attach_invoice(payment, user=user)

    async def sync_payment(self, payment: dict[str, Any]) -> dict[str, Any]:
        if payment["status"] == "completed":
            return payment
        invoice = await self._fetch_invoice_for_payment(payment)
        if invoice is None:
            return payment
        result = await self._apply_invoice(invoice)
        await self._notify_on_state_change(result)
        refreshed = await self.repo.get_payment_by_id(payment["id"])
        return refreshed or payment

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
                payments = await self._list_pending_payments(limit=50)
                for payment in payments:
                    try:
                        result = await self._sync_pending_payment(payment)
                        if result:
                            await self._notify_on_state_change(result)
                    except Exception:
                        logger.exception("Failed to sync %s payment %s", self.payment_type, payment.get("id"))
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=max(self.sync_interval_seconds(), 15))
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise

    async def _sync_pending_payment(self, payment: dict[str, Any]) -> dict[str, Any] | None:
        invoice = await self._fetch_invoice_for_payment(payment)
        if invoice is None:
            return await self.repo.mark_payment_expired_if_due(payment["id"])
        return await self._apply_invoice(invoice)

    async def _create_and_attach_invoice(self, payment: dict[str, Any], *, user: dict[str, Any]) -> dict[str, Any]:
        if not self.is_enabled():
            raise ValueError(tr(user.get("language_code"), self.disabled_error_key()))
        try:
            invoice = await self._create_invoice(payment, user=user)
        except Exception as exc:
            await self.repo.mark_payment_failed(payment["id"], str(exc), release_reservation=True)
            raise ValueError(self._public_error_message(exc, user.get("language_code"))) from exc
        updated = await self._attach_invoice(payment["id"], invoice)
        return updated

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
            await self.bot.send_message(
                user["tg_id"],
                tr(
                    lang,
                    "balance_topped_up",
                    balance_emoji=premium_emoji("balance"),
                    amount=format_money(payment["amount_cents"]),
                    balance=format_money(user["balance_cents"]),
                ),
            )
            return
        order = result.get("order") or {}
        await self.bot.send_message(
            user["tg_id"],
            tr(
                lang,
                "payment_success_notified",
                order_emoji=premium_emoji("order"),
                category_emoji=category_premium_emoji(order),
                product_title=html.quote(self.repo.localize_product_title(order, lang) or tr(lang, "shop_product_fallback")),
                price_emoji=premium_emoji("price"),
                amount=format_money(order.get("amount_cents", 0)),
                key_value=html.quote(order.get("key_value", "—")),
            ),
        )

    @staticmethod
    def _public_error_message(exc: Exception, language_code: str | None = "ru") -> str:
        if isinstance(exc, (ClientConnectorCertificateError, ssl.SSLCertVerificationError)):
            return tr(language_code, "secure_connection_error")
        if isinstance(exc, (ClientError, TimeoutError)):
            return tr(language_code, "gateway_unavailable")
        if isinstance(exc, (CryptoBotApiError, LolzteamApiError)):
            message = str(exc).strip()
            if not message or len(message) > 180:
                return tr(language_code, "invoice_create_failed")
            return message
        message = str(exc).strip()
        if not message or len(message) > 180:
            return tr(language_code, "invoice_create_failed")
        return message

    async def _build_description(self, payment: dict[str, Any], language_code: str | None) -> str:
        if payment["purpose"] == "deposit":
            return tr(language_code, "crypto_deposit_description")
        product = await self.repo.get_product(payment["product_id"])
        localized_product = self.repo.localize_product(product, language_code) if product else None
        product_name = localized_product["title"] if localized_product else tr(language_code, "shop_product_fallback")
        return tr(language_code, "crypto_product_description", product_name=product_name)

    async def _build_hidden_message(self, payment: dict[str, Any], language_code: str | None) -> str | None:
        if payment["purpose"] == "deposit":
            return tr(language_code, "crypto_deposit_hidden_message")
        return tr(language_code, "crypto_product_hidden_message")

    async def _create_payment_record(
        self,
        *,
        user_id: int,
        amount_cents: int,
        currency: str,
        purpose: str,
        product_id: int | None = None,
        lifetime_seconds: int,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def _create_invoice(self, payment: dict[str, Any], *, user: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def _fetch_invoice_for_payment(self, payment: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError

    async def _attach_invoice(self, payment_id: int, invoice: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def _apply_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def _list_pending_payments(self, limit: int) -> list[dict[str, Any]]:
        raise NotImplementedError

    def invoice_currency(self) -> str:
        raise NotImplementedError

    def invoice_lifetime_seconds(self) -> int:
        raise NotImplementedError

    def sync_interval_seconds(self) -> int:
        raise NotImplementedError

    def disabled_error_key(self) -> str:
        raise NotImplementedError

    def is_enabled(self) -> bool:
        raise NotImplementedError


class CryptoBotPaymentService(BasePaymentService):
    payment_type = "cryptobot"

    def __init__(
        self,
        *,
        repo: ShopRepository,
        config: Config,
        client: CryptoBotClient,
        bot: Bot,
    ) -> None:
        super().__init__(repo=repo, config=config, bot=bot)
        self.client = client

    def is_enabled(self) -> bool:
        return self.config.cryptopay_enabled

    def build_success_url(self, payment_id: int) -> str:
        if not self.config.public_base_url:
            return "https://t.me/"
        return f"{self.config.public_base_url}/payments/cryptobot/success?payment_id={payment_id}"

    def build_webhook_url(self) -> str | None:
        if not self.config.public_base_url or not self.config.cryptopay_webhook_path_token:
            return None
        return f"{self.config.public_base_url}/payments/cryptobot/webhook/{self.config.cryptopay_webhook_path_token}"

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
        age = abs((datetime.now(timezone.utc) - request_dt.astimezone(timezone.utc)).total_seconds())
        return age <= max(self.config.cryptopay_webhook_max_age_seconds, 0)

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
        invoice_id = invoice.get("invoice_id")
        if not invoice_id:
            raise ValueError("Webhook payload is missing invoice_id")
        canonical_invoice = await self.client.get_invoice(invoice_id=int(invoice_id))
        result = await self._apply_invoice(canonical_invoice)
        await self._notify_on_state_change(result)
        return result

    async def _create_payment_record(self, **kwargs: Any) -> dict[str, Any]:
        return await self.repo.create_payment(payment_type=self.payment_type, **kwargs)

    async def _create_invoice(self, payment: dict[str, Any], *, user: dict[str, Any]) -> dict[str, Any]:
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
        return await self.client.create_invoice(payload)

    async def _fetch_invoice_for_payment(self, payment: dict[str, Any]) -> dict[str, Any] | None:
        provider_invoice_id = payment.get("provider_invoice_id")
        if not provider_invoice_id:
            return None
        return await self.client.get_invoice(invoice_id=int(provider_invoice_id))

    async def _attach_invoice(self, payment_id: int, invoice: dict[str, Any]) -> dict[str, Any]:
        return await self.repo.attach_cryptobot_invoice(payment_id, invoice)

    async def _apply_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        return await self.repo.apply_cryptobot_invoice(invoice)

    async def _list_pending_payments(self, limit: int) -> list[dict[str, Any]]:
        return await self.repo.list_pending_payments(self.payment_type, limit=limit)

    def invoice_currency(self) -> str:
        return self.config.cryptopay_invoice_currency

    def invoice_lifetime_seconds(self) -> int:
        return self.config.cryptopay_invoice_lifetime

    def sync_interval_seconds(self) -> int:
        return self.config.cryptopay_sync_interval_seconds

    def disabled_error_key(self) -> str:
        return "cryptopay_not_configured"


class LolzteamPaymentService(BasePaymentService):
    payment_type = "lolzteam"

    def __init__(
        self,
        *,
        repo: ShopRepository,
        config: Config,
        client: LolzteamClient,
        bot: Bot,
    ) -> None:
        super().__init__(repo=repo, config=config, bot=bot)
        self.client = client

    def is_enabled(self) -> bool:
        return self.config.lolz_enabled

    def build_success_url(self, payment_id: int) -> str:
        if not self.config.public_base_url:
            return "https://t.me/"
        return f"{self.config.public_base_url}/payments/lolzteam/success?payment_id={payment_id}"

    def build_webhook_url(self) -> str | None:
        if not self.config.public_base_url or not self.config.lolz_webhook_path_token:
            return None
        return f"{self.config.public_base_url}/payments/lolzteam/callback/{self.config.lolz_webhook_path_token}"

    def verify_webhook_secret(self, secret: str | None) -> bool:
        expected = self.config.lolz_webhook_secret or self.config.lolz_merchant_token
        return bool(secret and expected and hmac.compare_digest(secret, expected))

    async def process_webhook(self, payload: dict[str, Any], *, secret: str | None) -> dict[str, Any]:
        if not self.verify_webhook_secret(secret):
            raise PermissionError("Invalid Lolzteam webhook secret")
        invoice_id = payload.get("invoice_id")
        payment_id = payload.get("payment_id")
        if not invoice_id and not payment_id:
            raise ValueError("Webhook payload is missing invoice identifiers")
        canonical_invoice = await self.client.get_invoice(
            invoice_id=int(invoice_id) if invoice_id else None,
            payment_id=str(payment_id) if payment_id else None,
        )
        result = await self._apply_invoice(canonical_invoice)
        await self._notify_on_state_change(result)
        return result

    async def _create_payment_record(self, **kwargs: Any) -> dict[str, Any]:
        return await self.repo.create_payment(payment_type=self.payment_type, **kwargs)

    async def _create_invoice(self, payment: dict[str, Any], *, user: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "merchant_id": self.config.lolz_merchant_id,
            "amount": float(self.client.cents_to_amount(payment["amount_cents"])),
            "currency": self.config.lolz_invoice_currency.lower(),
            "payment_id": payment["provider_payment_id"],
            "comment": await self._build_description(payment, user.get("language_code")),
            "lifetime": self.config.lolz_invoice_lifetime,
            "additional_data": json.dumps(
                {
                    "payment_db_id": payment["id"],
                    "purpose": payment["purpose"],
                    "product_id": payment.get("product_id"),
                    "tg_user_id": user["tg_id"],
                },
                ensure_ascii=True,
                separators=(",", ":"),
            ),
        }
        if self.config.lolz_is_test:
            payload["is_test"] = 1
        success_url = self.build_success_url(payment["id"])
        if success_url:
            payload["url_success"] = success_url
        webhook_url = self.build_webhook_url()
        if webhook_url:
            payload["url_callback"] = webhook_url
        if user.get("tg_id"):
            payload["required_telegram_id"] = int(user["tg_id"])
        username = str(user.get("username") or "").strip().lstrip("@")
        if username:
            payload["required_telegram_username"] = f"@{username}"
        return await self.client.create_invoice(payload)

    async def _fetch_invoice_for_payment(self, payment: dict[str, Any]) -> dict[str, Any] | None:
        provider_payment_id = payment.get("provider_payment_id")
        provider_invoice_id = payment.get("provider_invoice_id")
        if provider_payment_id:
            return await self.client.get_invoice(payment_id=str(provider_payment_id))
        if provider_invoice_id:
            return await self.client.get_invoice(invoice_id=int(provider_invoice_id))
        return None

    async def _attach_invoice(self, payment_id: int, invoice: dict[str, Any]) -> dict[str, Any]:
        return await self.repo.attach_lolzteam_invoice(payment_id, invoice)

    async def _apply_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        return await self.repo.apply_lolzteam_invoice(invoice)

    async def _list_pending_payments(self, limit: int) -> list[dict[str, Any]]:
        return await self.repo.list_pending_payments(self.payment_type, limit=limit)

    def invoice_currency(self) -> str:
        return self.config.lolz_invoice_currency

    def invoice_lifetime_seconds(self) -> int:
        return self.config.lolz_invoice_lifetime

    def sync_interval_seconds(self) -> int:
        return self.config.lolz_sync_interval_seconds

    def disabled_error_key(self) -> str:
        return "lolz_not_configured"


class PaymentService:
    def __init__(
        self,
        *,
        repo: ShopRepository,
        cryptobot: CryptoBotPaymentService,
        lolzteam: LolzteamPaymentService,
    ) -> None:
        self.repo = repo
        self.cryptobot = cryptobot
        self.lolzteam = lolzteam
        self._providers: dict[str, PaymentProvider] = {
            cryptobot.payment_type: cryptobot,
            lolzteam.payment_type: lolzteam,
        }

    def is_provider_enabled(self, payment_type: str) -> bool:
        provider = self._providers.get(payment_type)
        return bool(provider and provider.is_enabled())

    async def create_deposit_invoice(self, tg_user_id: int, amount_cents: int, payment_type: str) -> dict[str, Any]:
        provider = self._providers.get(payment_type)
        if not provider:
            raise ValueError("Unsupported payment provider")
        return await provider.create_deposit_invoice(tg_user_id, amount_cents)

    async def create_product_invoice(self, tg_user_id: int, product_id: int, payment_type: str) -> dict[str, Any]:
        provider = self._providers.get(payment_type)
        if not provider:
            raise ValueError("Unsupported payment provider")
        return await provider.create_product_invoice(tg_user_id, product_id)

    async def sync_payment_for_user(self, tg_user_id: int, payment_id: int) -> dict[str, Any]:
        payment = await self.repo.get_user_payment_by_id(tg_user_id, payment_id)
        if not payment:
            raise ValueError(tr("ru", "payment_not_found"))
        provider = self._providers.get(payment.get("payment_type", ""))
        if not provider:
            raise ValueError("Unsupported payment provider")
        return await provider.sync_payment(payment)

    async def start_background_sync(self) -> None:
        await self.cryptobot.start_background_sync()
        await self.lolzteam.start_background_sync()

    async def stop_background_sync(self) -> None:
        await self.cryptobot.stop_background_sync()
        await self.lolzteam.stop_background_sync()
