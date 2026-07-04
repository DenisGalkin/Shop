from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class Config:
    bot_token: str
    bot_username: str
    support_username: str
    admin_ids: set[int]
    database_path: str
    default_currency: str
    referral_reward_percent: int
    public_base_url: str
    app_host: str
    app_port: int
    heleket_api_base: str
    heleket_merchant_uuid: str
    heleket_api_key: str
    heleket_invoice_currency: str
    heleket_invoice_lifetime: int
    heleket_to_currency: str
    heleket_network: str
    heleket_is_payment_multiple: bool
    heleket_subtract_percent: int
    heleket_webhook_path_token: str
    heleket_sync_interval_seconds: int
    cryptopay_api_base: str
    cryptopay_api_token: str
    cryptopay_invoice_currency: str
    cryptopay_invoice_lifetime: int
    cryptopay_accepted_assets: tuple[str, ...]
    cryptopay_allow_comments: bool
    cryptopay_allow_anonymous: bool
    cryptopay_webhook_path_token: str
    cryptopay_webhook_max_age_seconds: int
    cryptopay_sync_interval_seconds: int
    lolz_api_base: str
    lolz_merchant_id: int
    lolz_api_token: str
    lolz_merchant_token: str
    lolz_webhook_secret: str
    lolz_invoice_currency: str
    lolz_invoice_lifetime: int
    lolz_webhook_path_token: str
    lolz_sync_interval_seconds: int
    lolz_is_test: bool
    platega_api_base: str
    platega_merchant_id: str
    platega_secret: str
    platega_payment_method: int
    platega_invoice_currency: str
    platega_usd_rub_rate: Decimal
    platega_invoice_lifetime_minutes: int
    platega_create_path: str
    platega_create_path_fallback: str
    platega_webhook_path_token: str
    platega_sync_interval_seconds: int
    admin_web_username: str
    admin_web_password: str
    admin_web_secret: str
    admin_web_session_ttl_hours: int

    @property
    def cryptopay_enabled(self) -> bool:
        return bool(self.cryptopay_api_token)

    @property
    def heleket_enabled(self) -> bool:
        return bool(self.heleket_merchant_uuid and self.heleket_api_key)

    @property
    def lolz_enabled(self) -> bool:
        return bool(self.lolz_merchant_id and self.lolz_api_token and self.lolz_merchant_token)

    @property
    def admin_web_enabled(self) -> bool:
        return bool(self.admin_web_username and self.admin_web_password)

    @property
    def platega_enabled(self) -> bool:
        return bool(self.platega_merchant_id and self.platega_secret)


def _parse_admin_ids(raw_value: str) -> set[int]:
    return {int(chunk.strip()) for chunk in raw_value.split(",") if chunk.strip()}


def _parse_bool(raw_value: str, default: bool = False) -> bool:
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(raw_value: str) -> tuple[str, ...]:
    return tuple(chunk.strip().upper() for chunk in raw_value.split(",") if chunk.strip())


def _parse_positive_decimal(raw_value: str, env_name: str) -> Decimal:
    try:
        value = Decimal(raw_value.strip())
    except (AttributeError, InvalidOperation) as exc:
        raise RuntimeError(f"{env_name} must be a valid positive number") from exc
    if value <= 0:
        raise RuntimeError(f"{env_name} must be greater than 0")
    return value


def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not configured")

    database_path = os.getenv("DATABASE_PATH", "data/shop.sqlite3")
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    heleket_merchant_uuid = os.getenv("HELEKET_MERCHANT_UUID", "").strip()
    heleket_api_key = os.getenv("HELEKET_API_KEY", "").strip()
    heleket_webhook_token = os.getenv("HELEKET_WEBHOOK_PATH_TOKEN", "").strip()
    if heleket_api_key and not heleket_webhook_token:
        heleket_webhook_token = sha256(heleket_api_key.encode("utf-8")).hexdigest()
    cryptopay_api_token = os.getenv("CRYPTOPAY_API_TOKEN", "").strip()
    cryptopay_webhook_token = os.getenv("CRYPTOPAY_WEBHOOK_PATH_TOKEN", "").strip()
    if cryptopay_api_token and not cryptopay_webhook_token:
        cryptopay_webhook_token = sha256(cryptopay_api_token.encode("utf-8")).hexdigest()
    lolz_api_token = os.getenv("LOLZ_API_TOKEN", "").strip()
    lolz_merchant_token = os.getenv("LOLZ_MERCHANT_TOKEN", "").strip()
    lolz_webhook_token = os.getenv("LOLZ_WEBHOOK_PATH_TOKEN", "").strip()
    if lolz_merchant_token and not lolz_webhook_token:
        lolz_webhook_token = sha256(lolz_merchant_token.encode("utf-8")).hexdigest()
    webhook_secret = os.getenv("LOLZ_WEBHOOK_SECRET", "").strip()
    if webhook_secret and lolz_merchant_token and webhook_secret != lolz_merchant_token:
        raise RuntimeError("LOLZ_WEBHOOK_SECRET must match LOLZ_MERCHANT_TOKEN according to Lolzteam webhook docs")
    if not webhook_secret:
        webhook_secret = lolz_merchant_token
    platega_merchant_id = os.getenv("PLATEGA_MERCHANT_ID", "").strip()
    platega_secret = os.getenv("PLATEGA_SECRET", "").strip()
    platega_webhook_token = os.getenv("PLATEGA_WEBHOOK_PATH_TOKEN", "").strip()
    if platega_secret and not platega_webhook_token:
        platega_webhook_token = sha256(platega_secret.encode("utf-8")).hexdigest()
    admin_web_secret = os.getenv("ADMIN_WEB_SECRET", "").strip()
    if not admin_web_secret:
        admin_web_secret = base64.urlsafe_b64encode(sha256(bot_token.encode("utf-8")).digest()).decode("ascii")

    config = Config(
        bot_token=bot_token,
        bot_username=os.getenv("BOT_USERNAME", "").strip(),
        support_username=os.getenv("SUPPORT_USERNAME", "support").strip().lstrip("@"),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        database_path=database_path,
        default_currency=os.getenv("DEFAULT_CURRENCY", "USD").strip().upper(),
        referral_reward_percent=int(os.getenv("REFERRAL_REWARD_PERCENT", "2")),
        public_base_url=os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/"),
        app_host=os.getenv("APP_HOST", "0.0.0.0").strip(),
        app_port=int(os.getenv("APP_PORT", "8080")),
        heleket_api_base=os.getenv("HELEKET_API_BASE", "https://api.heleket.com").strip().rstrip("/"),
        heleket_merchant_uuid=heleket_merchant_uuid,
        heleket_api_key=heleket_api_key,
        heleket_invoice_currency=os.getenv("HELEKET_INVOICE_CURRENCY", "USD").strip().upper(),
        heleket_invoice_lifetime=int(os.getenv("HELEKET_INVOICE_LIFETIME", "3600")),
        heleket_to_currency=os.getenv("HELEKET_TO_CURRENCY", "").strip().upper(),
        heleket_network=os.getenv("HELEKET_NETWORK", "").strip(),
        heleket_is_payment_multiple=_parse_bool(os.getenv("HELEKET_IS_PAYMENT_MULTIPLE"), default=True),
        heleket_subtract_percent=int(os.getenv("HELEKET_SUBTRACT_PERCENT", "0")),
        heleket_webhook_path_token=heleket_webhook_token,
        heleket_sync_interval_seconds=int(os.getenv("HELEKET_SYNC_INTERVAL_SECONDS", "60")),
        cryptopay_api_base=os.getenv("CRYPTOPAY_API_BASE", "https://pay.crypt.bot/api").strip().rstrip("/"),
        cryptopay_api_token=cryptopay_api_token,
        cryptopay_invoice_currency=os.getenv("CRYPTOPAY_INVOICE_CURRENCY", "USD").strip().upper(),
        cryptopay_invoice_lifetime=int(os.getenv("CRYPTOPAY_INVOICE_LIFETIME", "3600")),
        cryptopay_accepted_assets=_parse_csv(os.getenv("CRYPTOPAY_ACCEPTED_ASSETS", "")),
        cryptopay_allow_comments=_parse_bool(os.getenv("CRYPTOPAY_ALLOW_COMMENTS"), default=False),
        cryptopay_allow_anonymous=_parse_bool(os.getenv("CRYPTOPAY_ALLOW_ANONYMOUS"), default=False),
        cryptopay_webhook_path_token=cryptopay_webhook_token,
        cryptopay_webhook_max_age_seconds=int(os.getenv("CRYPTOPAY_WEBHOOK_MAX_AGE_SECONDS", "900")),
        cryptopay_sync_interval_seconds=int(os.getenv("CRYPTOPAY_SYNC_INTERVAL_SECONDS", "60")),
        lolz_api_base=os.getenv("LOLZ_API_BASE", "https://prod-api.lzt.market").strip().rstrip("/"),
        lolz_merchant_id=int(os.getenv("LOLZ_MERCHANT_ID", "0") or "0"),
        lolz_api_token=lolz_api_token,
        lolz_merchant_token=lolz_merchant_token,
        lolz_webhook_secret=webhook_secret,
        lolz_invoice_currency=os.getenv("LOLZ_INVOICE_CURRENCY", "USD").strip().upper(),
        lolz_invoice_lifetime=int(os.getenv("LOLZ_INVOICE_LIFETIME", "3600")),
        lolz_webhook_path_token=lolz_webhook_token,
        lolz_sync_interval_seconds=int(os.getenv("LOLZ_SYNC_INTERVAL_SECONDS", "60")),
        lolz_is_test=_parse_bool(os.getenv("LOLZ_IS_TEST"), default=False),
        platega_api_base=os.getenv("PLATEGA_API_BASE", "https://app.platega.io").strip().rstrip("/"),
        platega_merchant_id=platega_merchant_id,
        platega_secret=platega_secret,
        platega_payment_method=int(os.getenv("PLATEGA_PAYMENT_METHOD", "2")),
        platega_invoice_currency=os.getenv("PLATEGA_INVOICE_CURRENCY", "RUB").strip().upper(),
        platega_usd_rub_rate=_parse_positive_decimal(os.getenv("PLATEGA_USD_RUB_RATE", "80"), "PLATEGA_USD_RUB_RATE"),
        platega_invoice_lifetime_minutes=int(os.getenv("PLATEGA_INVOICE_LIFETIME_MINUTES", "15")),
        platega_create_path=os.getenv("PLATEGA_CREATE_PATH", "/transaction/process").strip(),
        platega_create_path_fallback=os.getenv("PLATEGA_CREATE_PATH_FALLBACK", "/v2/transaction/process").strip(),
        platega_webhook_path_token=platega_webhook_token,
        platega_sync_interval_seconds=int(os.getenv("PLATEGA_SYNC_INTERVAL_SECONDS", "60")),
        admin_web_username=os.getenv("ADMIN_WEB_USERNAME", "admin").strip(),
        admin_web_password=os.getenv("ADMIN_WEB_PASSWORD", "").strip(),
        admin_web_secret=admin_web_secret,
        admin_web_session_ttl_hours=int(os.getenv("ADMIN_WEB_SESSION_TTL_HOURS", "24")),
    )
    if any((lolz_api_token, lolz_merchant_token, str(config.lolz_merchant_id or "").strip(), webhook_secret, lolz_webhook_token)) and not config.lolz_enabled:
        raise RuntimeError(
            "Lolzteam requires LOLZ_MERCHANT_ID, LOLZ_API_TOKEN, and LOLZ_MERCHANT_TOKEN to be configured together"
        )
    if any((heleket_merchant_uuid, heleket_api_key, heleket_webhook_token)) and not config.heleket_enabled:
        raise RuntimeError("Heleket requires HELEKET_MERCHANT_UUID and HELEKET_API_KEY to be configured together")
    if not 0 <= config.heleket_subtract_percent <= 100:
        raise RuntimeError("HELEKET_SUBTRACT_PERCENT must be between 0 and 100")
    if any((platega_merchant_id, platega_secret, platega_webhook_token)) and not config.platega_enabled:
        raise RuntimeError("Platega requires PLATEGA_MERCHANT_ID and PLATEGA_SECRET to be configured together")
    if (config.heleket_enabled or config.cryptopay_enabled or config.lolz_enabled or config.platega_enabled) and not config.public_base_url:
        raise RuntimeError("PUBLIC_BASE_URL is required when payment providers are enabled")
    return config
