from __future__ import annotations

import os
from hashlib import sha256
from dataclasses import dataclass
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

    @property
    def cryptopay_enabled(self) -> bool:
        return bool(self.cryptopay_api_token)


def _parse_admin_ids(raw_value: str) -> set[int]:
    return {int(chunk.strip()) for chunk in raw_value.split(",") if chunk.strip()}


def _parse_bool(raw_value: str, default: bool = False) -> bool:
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(raw_value: str) -> tuple[str, ...]:
    return tuple(chunk.strip().upper() for chunk in raw_value.split(",") if chunk.strip())


def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not configured")

    database_path = os.getenv("DATABASE_PATH", "data/shop.sqlite3")
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    cryptopay_api_token = os.getenv("CRYPTOPAY_API_TOKEN", "").strip()
    webhook_token = os.getenv("CRYPTOPAY_WEBHOOK_PATH_TOKEN", "").strip()
    if cryptopay_api_token and not webhook_token:
        webhook_token = sha256(cryptopay_api_token.encode("utf-8")).hexdigest()

    return Config(
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
        cryptopay_api_base=os.getenv("CRYPTOPAY_API_BASE", "https://pay.crypt.bot/api").strip().rstrip("/"),
        cryptopay_api_token=cryptopay_api_token,
        cryptopay_invoice_currency=os.getenv("CRYPTOPAY_INVOICE_CURRENCY", "USD").strip().upper(),
        cryptopay_invoice_lifetime=int(os.getenv("CRYPTOPAY_INVOICE_LIFETIME", "3600")),
        cryptopay_accepted_assets=_parse_csv(os.getenv("CRYPTOPAY_ACCEPTED_ASSETS", "")),
        cryptopay_allow_comments=_parse_bool(os.getenv("CRYPTOPAY_ALLOW_COMMENTS"), default=False),
        cryptopay_allow_anonymous=_parse_bool(os.getenv("CRYPTOPAY_ALLOW_ANONYMOUS"), default=False),
        cryptopay_webhook_path_token=webhook_token,
        cryptopay_webhook_max_age_seconds=int(os.getenv("CRYPTOPAY_WEBHOOK_MAX_AGE_SECONDS", "900")),
        cryptopay_sync_interval_seconds=int(os.getenv("CRYPTOPAY_SYNC_INTERVAL_SECONDS", "60")),
    )
