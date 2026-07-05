from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite

from bot.config import Config
from bot.utils.i18n import SUPPORTED_LANGUAGES, normalize_language_code, pick_localized_text


PRODUCT_LOCALIZED_FIELDS = ("title", "description", "important_info")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def utcnow_iso() -> str:
    return utcnow().isoformat()


def epoch_to_iso(raw_value: int | float | None) -> str | None:
    if not raw_value:
        return None
    return datetime.fromtimestamp(raw_value, tz=timezone.utc).replace(microsecond=0).isoformat()


def parse_datetime_to_iso(raw_value: str | None) -> str | None:
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except ValueError:
        return None


def duration_to_expires_at_iso(raw_value: str | None, *, base_time: datetime | None = None) -> str | None:
    if not raw_value:
        return None
    parts = [chunk.strip() for chunk in str(raw_value).split(":")]
    if len(parts) != 3:
        return None
    try:
        hours, minutes, seconds = (int(chunk) for chunk in parts)
    except ValueError:
        return None
    if min(hours, minutes, seconds) < 0:
        return None
    start = (base_time or utcnow()).astimezone(timezone.utc).replace(microsecond=0)
    return (start + timedelta(hours=hours, minutes=minutes, seconds=seconds)).isoformat()


@dataclass(slots=True)
class PaginationResult:
    items: list[dict[str, Any]]
    page: int
    per_page: int
    total: int

    @property
    def pages(self) -> int:
        if self.total == 0:
            return 1
        return (self.total + self.per_page - 1) // self.per_page


class ShopRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        self._db: aiosqlite.Connection | None = None
        self._settings_cache: dict[str, str] = {}

    async def initialize(self, config: Config) -> None:
        self._db = await aiosqlite.connect(self.database_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._create_schema()
        await self._migrate_schema()
        await self._seed_settings(config)
        await self._seed_catalog()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Repository is not initialized")
        return self._db

    async def _fetchone(self, query: str, params: Sequence[Any] = ()) -> aiosqlite.Row | None:
        async with self.db.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def _fetchall(self, query: str, params: Sequence[Any] = ()) -> list[aiosqlite.Row]:
        async with self.db.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def _create_schema(self) -> None:
        await self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                full_name TEXT NOT NULL,
                balance_cents INTEGER NOT NULL DEFAULT 0,
                total_deposited_cents INTEGER NOT NULL DEFAULT 0,
                total_spent_cents INTEGER NOT NULL DEFAULT 0,
                referral_earned_cents INTEGER NOT NULL DEFAULT 0,
                referral_balance_cents INTEGER NOT NULL DEFAULT 0,
                referrer_user_id INTEGER,
                language_code TEXT NOT NULL DEFAULT 'ru',
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (referrer_user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                premium_emoji_id TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                title_i18n TEXT NOT NULL DEFAULT '{}',
                description TEXT NOT NULL DEFAULT '',
                description_i18n TEXT NOT NULL DEFAULT '{}',
                important_info TEXT NOT NULL DEFAULT '',
                important_info_i18n TEXT NOT NULL DEFAULT '{}',
                activation_link TEXT NOT NULL DEFAULT '',
                price_cents INTEGER NOT NULL,
                warranty_label TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );

            CREATE TABLE IF NOT EXISTS stock_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                key_value TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'available',
                order_id INTEGER,
                reserved_payment_id TEXT,
                reserved_until TEXT,
                created_at TEXT NOT NULL,
                sold_at TEXT,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                stock_item_id INTEGER,
                amount_cents INTEGER NOT NULL,
                status TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                payment_status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                payload_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (stock_item_id) REFERENCES stock_items(id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                payment_type TEXT NOT NULL,
                purpose TEXT NOT NULL DEFAULT 'deposit',
                product_id INTEGER,
                reserved_stock_item_id INTEGER,
                order_id INTEGER,
                provider_payment_id TEXT UNIQUE,
                provider_invoice_id INTEGER UNIQUE,
                provider_invoice_url TEXT,
                provider_status TEXT NOT NULL DEFAULT 'creating',
                merchant_id INTEGER,
                external_amount TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                error_text TEXT,
                meta_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT,
                processed_at TEXT,
                last_checked_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (reserved_stock_item_id) REFERENCES stock_items(id),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            );

            CREATE TABLE IF NOT EXISTS referral_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_user_id INTEGER NOT NULL,
                referred_user_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                reward_percent INTEGER NOT NULL,
                source_type TEXT NOT NULL,
                source_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (referrer_user_id) REFERENCES users(id),
                FOREIGN KEY (referred_user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stock_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, product_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE INDEX IF NOT EXISTS idx_users_tg_id ON users(tg_id);
            CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id, is_active, sort_order);
            CREATE INDEX IF NOT EXISTS idx_stock_product_status ON stock_items(product_id, status);
            CREATE INDEX IF NOT EXISTS idx_orders_user_created ON orders(user_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_stock_notifications_product ON stock_notifications(product_id);
            """
        )
        await self.db.commit()

    async def _migrate_schema(self) -> None:
        await self._drop_legacy_catalog_columns()
        await self._ensure_column("products", "title_i18n", "TEXT NOT NULL DEFAULT '{}'")
        await self._ensure_column("products", "description_i18n", "TEXT NOT NULL DEFAULT '{}'")
        await self._ensure_column("products", "important_info_i18n", "TEXT NOT NULL DEFAULT '{}'")
        await self._ensure_column("products", "activation_link", "TEXT NOT NULL DEFAULT ''")
        await self._ensure_column("categories", "premium_emoji_id", "TEXT")
        await self._ensure_column("stock_items", "reserved_payment_id", "TEXT")
        await self._ensure_column("stock_items", "reserved_until", "TEXT")
        await self._ensure_column("payments", "currency", "TEXT NOT NULL DEFAULT 'USD'")
        await self._ensure_column("payments", "purpose", "TEXT NOT NULL DEFAULT 'deposit'")
        await self._ensure_column("payments", "product_id", "INTEGER")
        await self._ensure_column("payments", "reserved_stock_item_id", "INTEGER")
        await self._ensure_column("payments", "order_id", "INTEGER")
        await self._ensure_column("payments", "provider_payment_id", "TEXT")
        await self._ensure_column("payments", "provider_invoice_id", "INTEGER")
        await self._ensure_column("payments", "provider_invoice_url", "TEXT")
        await self._ensure_column("payments", "provider_status", "TEXT NOT NULL DEFAULT 'creating'")
        await self._ensure_column("payments", "merchant_id", "INTEGER")
        await self._ensure_column("payments", "external_amount", "TEXT")
        await self._ensure_column("payments", "error_text", "TEXT")
        await self._ensure_column("payments", "updated_at", "TEXT")
        await self._ensure_column("payments", "expires_at", "TEXT")
        await self._ensure_column("payments", "processed_at", "TEXT")
        await self._ensure_column("payments", "last_checked_at", "TEXT")
        await self.db.execute(
            "UPDATE payments SET updated_at = COALESCE(updated_at, created_at, ?)",
            (utcnow_iso(),),
        )
        await self.db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_provider_payment_id ON payments(provider_payment_id)"
        )
        await self.db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_provider_invoice_id ON payments(provider_invoice_id)"
        )
        await self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_stock_reserved_until ON stock_items(status, reserved_until)"
        )
        await self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_payments_user_created ON payments(user_id, created_at DESC)"
        )
        await self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_payments_pending_sync ON payments(payment_type, status, expires_at, last_checked_at)"
        )
        await self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id, is_active, sort_order)"
        )
        category_default_icons = {
            "claude": "5341790816199286662",
            "chatgpt": "5341790652990530125",
            "grok": "5341553317392720144",
        }
        for slug, premium_emoji_id in category_default_icons.items():
            await self.db.execute(
                """
                UPDATE categories
                SET premium_emoji_id = ?
                WHERE slug = ?
                  AND COALESCE(TRIM(premium_emoji_id), '') = ''
                """,
                (premium_emoji_id, slug),
            )
        await self._backfill_product_localizations()
        await self.db.commit()

    @staticmethod
    def _parse_localized_json(raw_value: Any) -> dict[str, str]:
        if isinstance(raw_value, dict):
            source = raw_value
        elif isinstance(raw_value, str) and raw_value.strip():
            try:
                parsed = json.loads(raw_value)
            except json.JSONDecodeError:
                return {}
            if not isinstance(parsed, dict):
                return {}
            source = parsed
        else:
            return {}
        normalized: dict[str, str] = {}
        for language_code, text in source.items():
            lang = normalize_language_code(str(language_code))
            value = str(text or "").strip()
            if value:
                normalized[lang] = value
        return normalized

    @staticmethod
    def _dump_localized_json(values: dict[str, str] | None) -> str:
        normalized: dict[str, str] = {}
        for language_code in SUPPORTED_LANGUAGES:
            value = str((values or {}).get(language_code, "")).strip()
            if value:
                normalized[language_code] = value
        return json.dumps(normalized, ensure_ascii=False, sort_keys=True)

    def _coerce_localized_field(self, base_value: str, localized_values: dict[str, str] | None) -> dict[str, str]:
        values = self._parse_localized_json(localized_values)
        fallback = str(base_value or "").strip()
        if fallback and not values.get("ru"):
            values["ru"] = fallback
        return values

    def _attach_product_localizations(self, product: dict[str, Any]) -> dict[str, Any]:
        item = dict(product)
        for field_name in PRODUCT_LOCALIZED_FIELDS:
            item[f"{field_name}_i18n"] = self._coerce_localized_field(
                str(item.get(field_name, "") or ""),
                item.get(f"{field_name}_i18n"),
            )
        return item

    def localize_product(self, product: dict[str, Any] | None, language_code: str | None) -> dict[str, Any] | None:
        if not product:
            return None
        item = self._attach_product_localizations(product)
        for field_name in PRODUCT_LOCALIZED_FIELDS:
            item[field_name] = pick_localized_text(
                item.get(f"{field_name}_i18n"),
                language_code,
                str(item.get(field_name, "") or ""),
            )
        return item

    def localize_product_title(self, item: dict[str, Any] | None, language_code: str | None, *, field_name: str = "product_title") -> str:
        if not item:
            return ""
        localized_map = self._parse_localized_json(item.get(f"{field_name}_i18n"))
        return pick_localized_text(localized_map, language_code, str(item.get(field_name, "") or ""))

    async def _backfill_product_localizations(self) -> None:
        rows = await self._fetchall(
            """
            SELECT id, title, title_i18n, description, description_i18n, important_info, important_info_i18n
            FROM products
            """
        )
        for row in rows:
            updates: dict[str, str] = {}
            for field_name in PRODUCT_LOCALIZED_FIELDS:
                values = self._coerce_localized_field(
                    str(row[field_name] or ""),
                    row[f"{field_name}_i18n"],
                )
                if self._dump_localized_json(values) != str(row[f"{field_name}_i18n"] or ""):
                    updates[f"{field_name}_i18n"] = self._dump_localized_json(values)
            if updates:
                await self.db.execute(
                    """
                    UPDATE products
                    SET title_i18n = ?,
                        description_i18n = ?,
                        important_info_i18n = ?
                    WHERE id = ?
                    """,
                    (
                        updates.get("title_i18n", str(row["title_i18n"] or "{}")),
                        updates.get("description_i18n", str(row["description_i18n"] or "{}")),
                        updates.get("important_info_i18n", str(row["important_info_i18n"] or "{}")),
                        row["id"],
                    ),
                )

    async def _drop_legacy_catalog_columns(self) -> None:
        category_columns = {row["name"] for row in await self._fetchall("PRAGMA table_info(categories)")}
        if "description" in category_columns:
            await self._rebuild_categories_without_description()
        product_columns = {row["name"] for row in await self._fetchall("PRAGMA table_info(products)")}
        if "internal_name" in product_columns or "internal_name_i18n" in product_columns:
            await self._rebuild_products_without_internal_name()
        await self._rebuild_stock_items_if_legacy_product_fk()
        await self._rebuild_stock_notifications_if_legacy_product_fk()

    async def _rebuild_categories_without_description(self) -> None:
        await self.db.execute("PRAGMA foreign_keys=OFF")
        await self.db.execute("ALTER TABLE categories RENAME TO categories_legacy")
        await self.db.execute(
            """
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                premium_emoji_id TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        await self.db.execute(
            """
            INSERT INTO categories(id, slug, title, premium_emoji_id, sort_order, is_active, created_at)
            SELECT id, slug, title, premium_emoji_id, sort_order, is_active, created_at
            FROM categories_legacy
            """
        )
        await self.db.execute("DROP TABLE categories_legacy")
        await self.db.execute("PRAGMA foreign_keys=ON")

    async def _rebuild_products_without_internal_name(self) -> None:
        await self.db.execute("PRAGMA foreign_keys=OFF")
        await self.db.execute("ALTER TABLE products RENAME TO products_legacy")
        await self.db.execute(
            """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                title_i18n TEXT NOT NULL DEFAULT '{}',
                description TEXT NOT NULL DEFAULT '',
                description_i18n TEXT NOT NULL DEFAULT '{}',
                important_info TEXT NOT NULL DEFAULT '',
                important_info_i18n TEXT NOT NULL DEFAULT '{}',
                activation_link TEXT NOT NULL DEFAULT '',
                price_cents INTEGER NOT NULL,
                warranty_label TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
            """
        )
        await self.db.execute(
            """
            INSERT INTO products(
                id, category_id, slug, title, title_i18n, description, description_i18n,
                important_info, important_info_i18n, activation_link, price_cents, warranty_label, is_active,
                sort_order, created_at
            )
            SELECT
                id, category_id, slug, title, title_i18n, description, description_i18n,
                important_info, important_info_i18n, '', price_cents, warranty_label, is_active,
                sort_order, created_at
            FROM products_legacy
            """
        )
        await self.db.execute("DROP TABLE products_legacy")
        await self.db.execute("PRAGMA foreign_keys=ON")

    async def _rebuild_stock_notifications_if_legacy_product_fk(self) -> None:
        foreign_keys = await self._fetchall("PRAGMA foreign_key_list(stock_notifications)")
        if not foreign_keys:
            return
        references_legacy_products = any(row["table"] == "products_legacy" for row in foreign_keys)
        if not references_legacy_products:
            return

        await self.db.execute("PRAGMA foreign_keys=OFF")
        await self.db.execute("ALTER TABLE stock_notifications RENAME TO stock_notifications_legacy")
        await self.db.execute(
            """
            CREATE TABLE stock_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, product_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """
        )
        await self.db.execute(
            """
            INSERT INTO stock_notifications(id, user_id, product_id, created_at)
            SELECT id, user_id, product_id, created_at
            FROM stock_notifications_legacy
            """
        )
        await self.db.execute("DROP TABLE stock_notifications_legacy")
        await self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_stock_notifications_product ON stock_notifications(product_id)"
        )
        await self.db.execute("PRAGMA foreign_keys=ON")

    async def _rebuild_stock_items_if_legacy_product_fk(self) -> None:
        foreign_keys = await self._fetchall("PRAGMA foreign_key_list(stock_items)")
        if not foreign_keys:
            return
        references_legacy_products = any(row["table"] == "products_legacy" for row in foreign_keys)
        if not references_legacy_products:
            return

        await self.db.execute("PRAGMA foreign_keys=OFF")
        await self.db.execute("ALTER TABLE stock_items RENAME TO stock_items_legacy")
        await self.db.execute(
            """
            CREATE TABLE stock_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                key_value TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'available',
                order_id INTEGER,
                reserved_payment_id TEXT,
                reserved_until TEXT,
                created_at TEXT NOT NULL,
                sold_at TEXT,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
            """
        )
        await self.db.execute(
            """
            INSERT INTO stock_items(
                id, product_id, key_value, status, order_id, reserved_payment_id, reserved_until, created_at, sold_at
            )
            SELECT
                id, product_id, key_value, status, order_id, reserved_payment_id, reserved_until, created_at, sold_at
            FROM stock_items_legacy
            """
        )
        await self.db.execute("DROP TABLE stock_items_legacy")
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_stock_product_status ON stock_items(product_id, status)")
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_stock_reserved_until ON stock_items(status, reserved_until)")
        await self.db.execute("PRAGMA foreign_keys=ON")

    async def _ensure_column(self, table_name: str, column_name: str, ddl: str) -> None:
        columns = await self._fetchall(f"PRAGMA table_info({table_name})")
        if any(row["name"] == column_name for row in columns):
            return
        await self.db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}")

    async def _seed_settings(self, config: Config) -> None:
        settings = {
            "support_username": config.support_username,
            "bot_username": config.bot_username,
            "default_currency": config.default_currency,
            "referral_reward_percent": str(config.referral_reward_percent),
            "platega_usd_rub_rate": str(config.platega_usd_rub_rate),
        }
        for key, value in settings.items():
            await self.db.execute(
                """
                INSERT INTO settings(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO NOTHING
                """,
                (key, value),
            )
        await self.db.commit()
        self._settings_cache.update(settings)

    async def _seed_catalog(self) -> None:
        category_rows = await self._fetchall("SELECT COUNT(*) AS count FROM categories")
        if category_rows[0]["count"] > 0:
            return
        now = utcnow_iso()
        categories = [
            ("claude", "Claude", "5341790816199286662", 10),
            ("chatgpt", "ChatGPT", "5341790652990530125", 20),
            ("grok", "Grok AI", "5341553317392720144", 30),
        ]
        for slug, title, premium_emoji_id, sort_order in categories:
            await self.db.execute(
                """
                INSERT INTO categories(slug, title, premium_emoji_id, sort_order, created_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (slug, title, premium_emoji_id, sort_order, now),
            )
        await self.db.commit()

        category_map = {row["slug"]: row["id"] for row in await self._fetchall("SELECT id, slug FROM categories")}
        products = [
            {
                "category_slug": "claude",
                "slug": "claude-max-5x",
                "title": "CDK Claude Max 5x",
                "description": (
                    "CDK (ключ) для самостоятельной активации подписки по session key "
                    "на любой аккаунт без активной подписки."
                ),
                "important_info": (
                    "Товар отпускается без гарантии. Для снижения рисков используйте "
                    "качественные приватные прокси или VPN."
                ),
                "title_i18n": {"ru": "CDK Claude Max 5x", "en": "CDK Claude Max 5x", "uk": "CDK Claude Max 5x"},
                "description_i18n": {
                    "ru": (
                        "CDK (ключ) для самостоятельной активации подписки по session key "
                        "на любой аккаунт без активной подписки."
                    ),
                    "en": (
                        "CDK key for self-activating a subscription via session key "
                        "on any account without an active subscription."
                    ),
                    "uk": (
                        "CDK-ключ для самостійної активації підписки через session key "
                        "на будь-якому акаунті без активної підписки."
                    ),
                },
                "important_info_i18n": {
                    "ru": (
                        "Товар отпускается без гарантии. Для снижения рисков используйте "
                        "качественные приватные прокси или VPN."
                    ),
                    "en": (
                        "This item is sold without warranty. To reduce risks, use "
                        "high-quality private proxies or a VPN."
                    ),
                    "uk": (
                        "Товар продається без гарантії. Для зниження ризиків використовуйте "
                        "якісні приватні проксі або VPN."
                    ),
                },
                "price_cents": 8000,
                "warranty_label": "No Warranty",
                "sort_order": 10,
            },
            {
                "category_slug": "claude",
                "slug": "claude-max-20x",
                "title": "CDK Claude Max 20x",
                "description": "Ключ для активации Claude Max с увеличенным лимитом использования.",
                "important_info": "Рекомендуется активация на чистом аккаунте с качественным IP.",
                "title_i18n": {"ru": "CDK Claude Max 20x", "en": "CDK Claude Max 20x", "uk": "CDK Claude Max 20x"},
                "description_i18n": {
                    "ru": "Ключ для активации Claude Max с увеличенным лимитом использования.",
                    "en": "Activation key for Claude Max with a higher usage limit.",
                    "uk": "Ключ для активації Claude Max зі збільшеним лімітом використання.",
                },
                "important_info_i18n": {
                    "ru": "Рекомендуется активация на чистом аккаунте с качественным IP.",
                    "en": "Activation on a clean account with a high-quality IP is recommended.",
                    "uk": "Рекомендується активація на чистому акаунті з якісною IP-адресою.",
                },
                "price_cents": 11000,
                "warranty_label": "No Warranty",
                "sort_order": 20,
            },
            {
                "category_slug": "chatgpt",
                "slug": "chatgpt-plus",
                "title": "ChatGPT Plus",
                "description": "Доступ к ChatGPT Plus в формате цифрового ключа или инструкции.",
                "important_info": "После покупки вы получите ключ или инструкцию в зависимости от поставки.",
                "title_i18n": {"ru": "ChatGPT Plus", "en": "ChatGPT Plus", "uk": "ChatGPT Plus"},
                "description_i18n": {
                    "ru": "Доступ к ChatGPT Plus в формате цифрового ключа или инструкции.",
                    "en": "Access to ChatGPT Plus as a digital key or activation instructions.",
                    "uk": "Доступ до ChatGPT Plus у форматі цифрового ключа або інструкції.",
                },
                "important_info_i18n": {
                    "ru": "После покупки вы получите ключ или инструкцию в зависимости от поставки.",
                    "en": "After purchase, you will receive either a key or activation instructions depending on the stock.",
                    "uk": "Після покупки ви отримаєте ключ або інструкцію залежно від поставки.",
                },
                "price_cents": 2200,
                "warranty_label": "Activation Support",
                "sort_order": 10,
            },
            {
                "category_slug": "grok",
                "slug": "grok-premium",
                "title": "Grok AI Premium",
                "description": "Доступ к премиальному тарифу Grok AI.",
                "important_info": "Перед покупкой уточните совместимость с вашим регионом.",
                "title_i18n": {"ru": "Grok AI Premium", "en": "Grok AI Premium", "uk": "Grok AI Premium"},
                "description_i18n": {
                    "ru": "Доступ к премиальному тарифу Grok AI.",
                    "en": "Access to the premium Grok AI plan.",
                    "uk": "Доступ до преміального тарифу Grok AI.",
                },
                "important_info_i18n": {
                    "ru": "Перед покупкой уточните совместимость с вашим регионом.",
                    "en": "Please confirm compatibility with your region before purchase.",
                    "uk": "Перед покупкою уточніть сумісність із вашим регіоном.",
                },
                "price_cents": 3000,
                "warranty_label": "Activation Support",
                "sort_order": 10,
            },
        ]
        for product in products:
            await self.db.execute(
                """
                INSERT INTO products(
                    category_id, slug, title, title_i18n, description, description_i18n, important_info, important_info_i18n,
                    price_cents, warranty_label, sort_order, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    category_map[product["category_slug"]],
                    product["slug"],
                    product["title"],
                    self._dump_localized_json(product.get("title_i18n")),
                    product["description"],
                    self._dump_localized_json(product.get("description_i18n")),
                    product["important_info"],
                    self._dump_localized_json(product.get("important_info_i18n")),
                    product["price_cents"],
                    product["warranty_label"],
                    product["sort_order"],
                    now,
                ),
            )
        await self.db.commit()

    async def get_settings(self) -> dict[str, str]:
        if not self._settings_cache:
            rows = await self._fetchall("SELECT key, value FROM settings")
            self._settings_cache = {row["key"]: row["value"] for row in rows}
        return dict(self._settings_cache)

    async def get_setting(self, key: str, default: str = "") -> str:
        settings = await self.get_settings()
        return settings.get(key, default)

    async def set_setting(self, key: str, value: str) -> None:
        await self.db.execute(
            """
            INSERT INTO settings(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await self.db.commit()
        self._settings_cache[key] = value

    async def upsert_user(
        self,
        tg_id: int,
        username: str | None,
        full_name: str,
        language_code: str | None,
        referrer_tg_id: int | None = None,
        admin_ids: set[int] | None = None,
    ) -> dict[str, Any]:
        admin_ids = admin_ids or set()
        row = await self._fetchone("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        normalized_language = normalize_language_code(language_code)
        if row is None:
            referrer_id = None
            if referrer_tg_id and referrer_tg_id != tg_id:
                referrer_row = await self._fetchone("SELECT id FROM users WHERE tg_id = ?", (referrer_tg_id,))
                referrer_id = referrer_row["id"] if referrer_row else None
            await self.db.execute(
                """
                INSERT INTO users(
                    tg_id, username, full_name, referrer_user_id, language_code, is_admin, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (tg_id, username, full_name, referrer_id, normalized_language, int(tg_id in admin_ids), utcnow_iso()),
            )
            await self.db.commit()
        else:
            resolved_language = normalize_language_code(row["language_code"]) if row["language_code"] else normalized_language
            await self.db.execute(
                """
                UPDATE users
                SET username = ?, full_name = ?, language_code = ?, is_admin = ?
                WHERE tg_id = ?
                """,
                (username, full_name, resolved_language, int(tg_id in admin_ids or row["is_admin"]), tg_id),
            )
            await self.db.commit()
        updated = await self._fetchone("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        return dict(updated)

    async def set_user_language(self, tg_id: int, language_code: str) -> dict[str, Any] | None:
        normalized_language = normalize_language_code(language_code)
        await self.db.execute(
            "UPDATE users SET language_code = ? WHERE tg_id = ?",
            (normalized_language, tg_id),
        )
        await self.db.commit()
        return await self.get_user_by_tg_id(tg_id)

    async def get_user_by_tg_id(self, tg_id: int) -> dict[str, Any] | None:
        row = await self._fetchone("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        return dict(row) if row else None

    async def get_user_stats(self, user_id: int) -> dict[str, Any]:
        user = await self._fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        referrals = await self._fetchone("SELECT COUNT(*) AS count FROM users WHERE referrer_user_id = ?", (user_id,))
        purchases = await self._fetchone(
            "SELECT COUNT(*) AS count FROM orders WHERE user_id = ? AND status = 'completed'",
            (user_id,),
        )
        return {**dict(user), "referrals_count": referrals["count"], "purchases_count": purchases["count"]}

    async def list_admin_users(self, search: str = "", limit: int = 50) -> list[dict[str, Any]]:
        normalized = search.strip()
        params: list[Any] = []
        query = """
            SELECT u.*,
                   COALESCE(stats.orders_count, 0) AS orders_count
            FROM users u
            LEFT JOIN (
                SELECT user_id, COUNT(*) AS orders_count
                FROM orders
                WHERE status = 'completed'
                GROUP BY user_id
            ) stats ON stats.user_id = u.id
        """
        if normalized:
            pattern = f"%{normalized.lower()}%"
            query += """
                WHERE CAST(u.tg_id AS TEXT) LIKE ?
                   OR LOWER(COALESCE(u.username, '')) LIKE ?
                   OR LOWER(u.full_name) LIKE ?
            """
            params.extend([pattern, pattern, pattern])
        query += " ORDER BY u.id DESC LIMIT ?"
        params.append(limit)
        rows = await self._fetchall(query, params)
        return [dict(row) for row in rows]

    async def release_expired_reservations(self) -> int:
        cursor = await self.db.execute(
            """
            UPDATE stock_items
            SET status = 'available',
                reserved_payment_id = NULL,
                reserved_until = NULL
            WHERE status = 'reserved'
              AND reserved_until IS NOT NULL
              AND reserved_until <= ?
              AND NOT EXISTS (
                  SELECT 1
                  FROM payments p
                  WHERE p.provider_payment_id = stock_items.reserved_payment_id
                    AND p.status = 'completed'
              )
            """,
            (utcnow_iso(),),
        )
        await self.db.commit()
        return cursor.rowcount or 0

    async def list_categories(self, only_active: bool = True) -> list[dict[str, Any]]:
        query = "SELECT * FROM categories"
        if only_active:
            query += " WHERE is_active = 1"
        query += " ORDER BY sort_order ASC, id ASC"
        rows = await self._fetchall(query)
        return [dict(row) for row in rows]

    async def list_admin_categories(self) -> list[dict[str, Any]]:
        rows = await self._fetchall(
            """
            SELECT c.*,
                   COUNT(DISTINCT p.id) AS products_count,
                   COALESCE(SUM(CASE WHEN p.is_active = 1 THEN 1 ELSE 0 END), 0) AS active_products_count,
                   COALESCE(SUM(CASE WHEN s.status = 'available' THEN 1 ELSE 0 END), 0) AS stock_total
            FROM categories c
            LEFT JOIN products p ON p.category_id = c.id
            LEFT JOIN stock_items s ON s.product_id = p.id
            GROUP BY c.id
            ORDER BY c.sort_order ASC, c.id ASC
            """
        )
        return [dict(row) for row in rows]

    async def get_category(self, category_id: int) -> dict[str, Any] | None:
        row = await self._fetchone("SELECT * FROM categories WHERE id = ?", (category_id,))
        return dict(row) if row else None

    async def create_category(self, title: str, premium_emoji_id: str | None = None) -> int:
        slug = await self._unique_slug("categories", title)
        cursor = await self.db.execute(
            "INSERT INTO categories(slug, title, premium_emoji_id, created_at) VALUES(?, ?, ?, ?)",
            (slug, title, premium_emoji_id, utcnow_iso()),
        )
        await self.db.commit()
        return cursor.lastrowid

    async def update_category(
        self,
        category_id: int,
        title: str,
        sort_order: int,
        premium_emoji_id: str | None = None,
    ) -> None:
        await self.db.execute(
            """
            UPDATE categories
            SET title = ?, sort_order = ?, premium_emoji_id = ?
            WHERE id = ?
            """,
            (title, sort_order, premium_emoji_id, category_id),
        )
        await self.db.commit()

    async def toggle_category(self, category_id: int) -> None:
        await self.db.execute(
            """
            UPDATE categories
            SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END
            WHERE id = ?
            """,
            (category_id,),
        )
        await self.db.commit()

    async def reorder_categories(self, category_ids: Sequence[int]) -> None:
        for sort_order, category_id in enumerate(category_ids):
            await self.db.execute(
                "UPDATE categories SET sort_order = ? WHERE id = ?",
                (sort_order, category_id),
            )
        await self.db.commit()

    async def delete_category(self, category_id: int) -> None:
        category_row = await self._fetchone("SELECT 1 FROM categories WHERE id = ? LIMIT 1", (category_id,))
        if not category_row:
            raise ValueError("Category not found")

        product_counts = await self._fetchone(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_total
            FROM products
            WHERE category_id = ?
            """,
            (category_id,),
        )
        total = int(product_counts["total"] or 0) if product_counts else 0
        active_total = int(product_counts["active_total"] or 0) if product_counts else 0
        if total > 0:
            hidden_total = total - active_total
            if active_total and hidden_total:
                raise ValueError(
                    f"This category cannot be deleted yet: it still contains {total} products ({active_total} active, {hidden_total} hidden)"
                )
            if active_total:
                raise ValueError(f"This category cannot be deleted yet: it still contains {active_total} active products")
            raise ValueError(f"This category cannot be deleted yet: it still contains {hidden_total} hidden products")

        await self.db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        await self.db.commit()

    async def list_products(self, category_id: int, only_active: bool = True) -> list[dict[str, Any]]:
        await self.release_expired_reservations()
        query = """
            SELECT p.*, c.title AS category_title, c.slug AS category_slug, c.premium_emoji_id AS category_premium_emoji_id,
                   COALESCE(stock.available_count, 0) AS stock_count
            FROM products p
            JOIN categories c ON c.id = p.category_id
            LEFT JOIN (
                SELECT product_id, COUNT(*) AS available_count
                FROM stock_items
                WHERE status = 'available'
                GROUP BY product_id
            ) stock ON stock.product_id = p.id
            WHERE p.category_id = ?
        """
        params: list[Any] = [category_id]
        if only_active:
            query += " AND p.is_active = 1"
        query += " ORDER BY p.sort_order ASC, p.id ASC"
        rows = await self._fetchall(query, params)
        return [self._attach_product_localizations(dict(row)) for row in rows]

    async def list_admin_products(self, search: str = "", category_id: int | None = None) -> list[dict[str, Any]]:
        await self.release_expired_reservations()
        normalized = search.strip()
        query = """
            SELECT p.*, c.title AS category_title, c.slug AS category_slug, c.premium_emoji_id AS category_premium_emoji_id,
                   COALESCE(stock.available_count, 0) AS stock_count,
                   COALESCE(stock.sold_count, 0) AS sold_count
            FROM products p
            JOIN categories c ON c.id = p.category_id
            LEFT JOIN (
                SELECT product_id,
                       SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) AS available_count,
                       SUM(CASE WHEN status = 'sold' THEN 1 ELSE 0 END) AS sold_count
                FROM stock_items
                GROUP BY product_id
            ) stock ON stock.product_id = p.id
            WHERE 1 = 1
        """
        params: list[Any] = []
        if category_id is not None:
            query += " AND p.category_id = ?"
            params.append(category_id)
        if normalized:
            pattern = f"%{normalized.lower()}%"
            query += """
                AND (
                    LOWER(p.title) LIKE ?
                    OR LOWER(c.title) LIKE ?
                )
            """
            params.extend([pattern, pattern])
        query += " ORDER BY c.sort_order ASC, p.sort_order ASC, p.id ASC"
        rows = await self._fetchall(query, params)
        return [self._attach_product_localizations(dict(row)) for row in rows]

    async def get_product(self, product_id: int) -> dict[str, Any] | None:
        await self.release_expired_reservations()
        row = await self._fetchone(
            """
            SELECT p.*, c.title AS category_title, c.slug AS category_slug, c.premium_emoji_id AS category_premium_emoji_id,
                   COALESCE(stock.available_count, 0) AS stock_count
            FROM products p
            JOIN categories c ON c.id = p.category_id
            LEFT JOIN (
                SELECT product_id, COUNT(*) AS available_count
                FROM stock_items
                WHERE status = 'available'
                GROUP BY product_id
            ) stock ON stock.product_id = p.id
            WHERE p.id = ?
            """,
            (product_id,),
        )
        return self._attach_product_localizations(dict(row)) if row else None

    async def create_product(
        self,
        category_id: int,
        title: str,
        price_cents: int,
        description: str,
        important_info: str,
        warranty_label: str,
        *,
        title_i18n: dict[str, str] | None = None,
        description_i18n: dict[str, str] | None = None,
        important_info_i18n: dict[str, str] | None = None,
        activation_link: str = "",
    ) -> int:
        slug = await self._unique_slug("products", title)
        cursor = await self.db.execute(
            """
            INSERT INTO products(
                category_id, slug, title, title_i18n, description, description_i18n, important_info, important_info_i18n,
                activation_link, price_cents, warranty_label, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                category_id,
                slug,
                title,
                self._dump_localized_json(self._coerce_localized_field(title, title_i18n)),
                description,
                self._dump_localized_json(self._coerce_localized_field(description, description_i18n)),
                important_info,
                self._dump_localized_json(self._coerce_localized_field(important_info, important_info_i18n)),
                str(activation_link or "").strip(),
                price_cents,
                warranty_label,
                utcnow_iso(),
            ),
        )
        await self.db.commit()
        return cursor.lastrowid

    async def update_product_field(self, product_id: int, field_name: str, value: Any) -> None:
        allowed_fields = {
            "title",
            "title_i18n",
            "description",
            "description_i18n",
            "important_info",
            "important_info_i18n",
            "activation_link",
            "price_cents",
            "warranty_label",
        }
        if field_name not in allowed_fields:
            raise ValueError(f"Unsupported field: {field_name}")
        await self.db.execute(f"UPDATE products SET {field_name} = ? WHERE id = ?", (value, product_id))
        await self.db.commit()

    async def update_product(
        self,
        product_id: int,
        *,
        category_id: int,
        title: str,
        description: str,
        important_info: str,
        price_cents: int,
        warranty_label: str,
        sort_order: int,
        title_i18n: dict[str, str] | None = None,
        description_i18n: dict[str, str] | None = None,
        important_info_i18n: dict[str, str] | None = None,
        activation_link: str = "",
    ) -> None:
        await self.db.execute(
            """
            UPDATE products
            SET category_id = ?,
                title = ?,
                title_i18n = ?,
                description = ?,
                description_i18n = ?,
                important_info = ?,
                important_info_i18n = ?,
                activation_link = ?,
                price_cents = ?,
                warranty_label = ?,
                sort_order = ?
            WHERE id = ?
            """,
            (
                category_id,
                title,
                self._dump_localized_json(self._coerce_localized_field(title, title_i18n)),
                description,
                self._dump_localized_json(self._coerce_localized_field(description, description_i18n)),
                important_info,
                self._dump_localized_json(self._coerce_localized_field(important_info, important_info_i18n)),
                str(activation_link or "").strip(),
                price_cents,
                warranty_label,
                sort_order,
                product_id,
            ),
        )
        await self.db.commit()

    async def toggle_product(self, product_id: int) -> None:
        await self.db.execute(
            """
            UPDATE products
            SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END
            WHERE id = ?
            """,
            (product_id,),
        )
        await self.db.commit()

    async def reorder_products(self, product_ids: Sequence[int]) -> None:
        for sort_order, product_id in enumerate(product_ids):
            await self.db.execute(
                "UPDATE products SET sort_order = ? WHERE id = ?",
                (sort_order, product_id),
            )
        await self.db.commit()

    async def delete_product(self, product_id: int) -> None:
        product_row = await self._fetchone("SELECT 1 FROM products WHERE id = ? LIMIT 1", (product_id,))
        if not product_row:
            raise ValueError("Product not found")

        order_row = await self._fetchone("SELECT 1 FROM orders WHERE product_id = ? LIMIT 1", (product_id,))
        if order_row:
            raise ValueError("This product cannot be deleted because it already has related orders")

        payment_row = await self._fetchone("SELECT 1 FROM payments WHERE product_id = ? LIMIT 1", (product_id,))
        if payment_row:
            raise ValueError("This product cannot be deleted because it already has related payments")

        stock_item_order_row = await self._fetchone(
            """
            SELECT 1
            FROM orders
            WHERE stock_item_id IN (SELECT id FROM stock_items WHERE product_id = ?)
            LIMIT 1
            """,
            (product_id,),
        )
        if stock_item_order_row:
            raise ValueError("This product cannot be deleted because some of its keys are linked to orders")

        stock_item_payment_row = await self._fetchone(
            """
            SELECT 1
            FROM payments
            WHERE reserved_stock_item_id IN (SELECT id FROM stock_items WHERE product_id = ?)
            LIMIT 1
            """,
            (product_id,),
        )
        if stock_item_payment_row:
            raise ValueError("This product cannot be deleted because some of its keys are linked to payments")

        reserved_stock_row = await self._fetchone(
            """
            SELECT 1
            FROM stock_items
            WHERE product_id = ?
              AND (
                status != 'available'
                OR order_id IS NOT NULL
                OR reserved_payment_id IS NOT NULL
              )
            LIMIT 1
            """,
            (product_id,),
        )
        if reserved_stock_row:
            raise ValueError("This product cannot be deleted because it has sold or reserved keys")

        try:
            await self.db.execute("DELETE FROM stock_notifications WHERE product_id = ?", (product_id,))
            await self.db.execute("DELETE FROM stock_items WHERE product_id = ?", (product_id,))
            cursor = await self.db.execute("DELETE FROM products WHERE id = ?", (product_id,))
            await self.db.commit()
        except aiosqlite.IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("This product cannot be deleted because it already has related data") from exc
        if (cursor.rowcount or 0) == 0:
            raise ValueError("Product not found")

    async def add_stock_items(self, product_id: int, keys: Sequence[str]) -> tuple[int, int]:
        added = 0
        skipped = 0
        for key in keys:
            normalized = key.strip()
            if not normalized:
                continue
            try:
                await self.db.execute(
                    "INSERT INTO stock_items(product_id, key_value, created_at) VALUES(?, ?, ?)",
                    (product_id, normalized, utcnow_iso()),
                )
                added += 1
            except aiosqlite.IntegrityError:
                skipped += 1
        await self.db.commit()
        return added, skipped

    async def list_admin_stock_items(self, product_id: int) -> list[dict[str, Any]]:
        await self.release_expired_reservations()
        rows = await self._fetchall(
            """
            SELECT id, product_id, key_value, status, order_id, reserved_payment_id, reserved_until, created_at, sold_at
            FROM stock_items
            WHERE product_id = ?
            ORDER BY
                CASE status
                    WHEN 'available' THEN 0
                    WHEN 'reserved' THEN 1
                    WHEN 'sold' THEN 2
                    ELSE 3
                END,
                id DESC
            """,
            (product_id,),
        )
        return [dict(row) for row in rows]

    async def delete_admin_stock_item(self, product_id: int, stock_item_id: int) -> bool:
        await self.release_expired_reservations()
        row = await self._fetchone(
            "SELECT id, status FROM stock_items WHERE id = ? AND product_id = ?",
            (stock_item_id, product_id),
        )
        if row is None:
            return False
        if row["status"] != "available":
            raise ValueError("Можно удалить только доступный ключ, который еще не продан и не зарезервирован")
        await self.db.execute(
            "DELETE FROM stock_items WHERE id = ? AND product_id = ? AND status = 'available'",
            (stock_item_id, product_id),
        )
        await self.db.commit()
        return True

    async def get_available_stock_count(self, product_id: int) -> int:
        await self.release_expired_reservations()
        row = await self._fetchone(
            "SELECT COUNT(*) AS count FROM stock_items WHERE product_id = ? AND status = 'available'",
            (product_id,),
        )
        return int(row["count"]) if row else 0

    async def has_stock_notification(self, user_id: int, product_id: int) -> bool:
        row = await self._fetchone(
            "SELECT 1 FROM stock_notifications WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        )
        return row is not None

    async def toggle_stock_notification(self, user_id: int, product_id: int) -> bool:
        if await self.has_stock_notification(user_id, product_id):
            await self.db.execute(
                "DELETE FROM stock_notifications WHERE user_id = ? AND product_id = ?",
                (user_id, product_id),
            )
            await self.db.commit()
            return False
        await self.db.execute(
            "INSERT INTO stock_notifications(user_id, product_id, created_at) VALUES(?, ?, ?)",
            (user_id, product_id, utcnow_iso()),
        )
        await self.db.commit()
        return True

    async def get_stock_notification_recipients(self, product_id: int) -> list[dict[str, Any]]:
        rows = await self._fetchall(
            """
            SELECT u.tg_id, u.id AS user_id, u.language_code
            FROM stock_notifications sn
            JOIN users u ON u.id = sn.user_id
            WHERE sn.product_id = ?
            ORDER BY sn.id ASC
            """,
            (product_id,),
        )
        return [dict(row) for row in rows]

    async def get_main_menu_summary(self, user_id: int) -> dict[str, Any]:
        return await self.get_user_stats(user_id)

    async def list_user_orders(self, user_id: int, page: int, per_page: int = 10) -> PaginationResult:
        page = max(page, 1)
        total_row = await self._fetchone(
            "SELECT COUNT(*) AS count FROM orders WHERE user_id = ? AND status = 'completed'",
            (user_id,),
        )
        rows = await self._fetchall(
            """
            SELECT o.*, p.title AS product_title, c.slug AS category_slug, c.premium_emoji_id AS category_premium_emoji_id
                   , p.title_i18n AS product_title_i18n, p.activation_link
            FROM orders o
            JOIN products p ON p.id = o.product_id
            JOIN categories c ON c.id = p.category_id
            WHERE o.user_id = ? AND o.status = 'completed'
            ORDER BY o.id DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, per_page, (page - 1) * per_page),
        )
        return PaginationResult(
            items=[dict(row) for row in rows],
            page=page,
            per_page=per_page,
            total=total_row["count"],
        )

    async def get_order(self, user_id: int, order_id: int) -> dict[str, Any] | None:
        row = await self._fetchone(
            """
            SELECT o.*, p.title AS product_title, c.slug AS category_slug, c.premium_emoji_id AS category_premium_emoji_id, s.key_value
                   , p.title_i18n AS product_title_i18n, p.activation_link
            FROM orders o
            JOIN products p ON p.id = o.product_id
            JOIN categories c ON c.id = p.category_id
            LEFT JOIN stock_items s ON s.id = o.stock_item_id
            WHERE o.id = ? AND o.user_id = ?
            """,
            (order_id, user_id),
        )
        return dict(row) if row else None

    async def get_order_by_payment_id(self, payment_id: int) -> dict[str, Any] | None:
        row = await self._fetchone("SELECT user_id, order_id FROM payments WHERE id = ?", (payment_id,))
        if row is None or not row["order_id"]:
            return None
        return await self.get_order(row["user_id"], row["order_id"])

    async def create_payment(
        self,
        *,
        user_id: int,
        amount_cents: int,
        currency: str,
        payment_type: str,
        purpose: str,
        product_id: int | None = None,
        lifetime_seconds: int = 3600,
    ) -> dict[str, Any]:
        await self.release_expired_reservations()
        provider_payment_id = f"shop_{purpose}_{uuid.uuid4().hex}"
        reservation_expires_at = (utcnow() + timedelta(seconds=lifetime_seconds)).isoformat()
        await self.db.execute("BEGIN IMMEDIATE")
        try:
            user = await self._fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
            if user is None:
                raise ValueError("User not found")
            reserved_stock_item_id: int | None = None
            if purpose == "product_purchase":
                if product_id is None:
                    raise ValueError("Product is required")
                product = await self._fetchone("SELECT * FROM products WHERE id = ?", (product_id,))
                if product is None or product["is_active"] != 1:
                    raise ValueError("Товар недоступен")
                amount_cents = int(product["price_cents"])
                stock_item = await self._fetchone(
                    """
                    SELECT * FROM stock_items
                    WHERE product_id = ? AND status = 'available'
                    ORDER BY id ASC
                    LIMIT 1
                    """,
                    (product_id,),
                )
                if stock_item is None:
                    raise ValueError("Товар закончился")
                cursor = await self.db.execute(
                    """
                    UPDATE stock_items
                    SET status = 'reserved',
                        reserved_payment_id = ?,
                        reserved_until = ?
                    WHERE id = ? AND status = 'available'
                    """,
                    (provider_payment_id, reservation_expires_at, stock_item["id"]),
                )
                if (cursor.rowcount or 0) == 0:
                    raise ValueError("Не удалось зарезервировать товар")
                reserved_stock_item_id = int(stock_item["id"])
            cursor = await self.db.execute(
                """
                INSERT INTO payments(
                    user_id, amount_cents, currency, payment_type, purpose, product_id,
                    reserved_stock_item_id, provider_payment_id, provider_status, status,
                    meta_json, created_at, updated_at, expires_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, 'creating', 'pending', '{}', ?, ?, ?)
                """,
                (
                    user_id,
                    amount_cents,
                    currency,
                    payment_type,
                    purpose,
                    product_id,
                    reserved_stock_item_id,
                    provider_payment_id,
                    utcnow_iso(),
                    utcnow_iso(),
                    reservation_expires_at,
                ),
            )
            payment_id = cursor.lastrowid
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        payment = await self.get_payment_by_id(payment_id)
        return payment or {}

    async def create_crypto_payment(
        self,
        *,
        user_id: int,
        amount_cents: int,
        currency: str,
        purpose: str,
        product_id: int | None = None,
        lifetime_seconds: int = 3600,
    ) -> dict[str, Any]:
        return await self.create_payment(
            user_id=user_id,
            amount_cents=amount_cents,
            currency=currency,
            payment_type="cryptobot",
            purpose=purpose,
            product_id=product_id,
            lifetime_seconds=lifetime_seconds,
        )

    async def get_payment_by_id(self, payment_id: int) -> dict[str, Any] | None:
        row = await self._fetchone(
            """
            SELECT p.*, u.tg_id, u.username, u.full_name, u.language_code, pr.title AS product_title
                   , pr.title_i18n AS product_title_i18n
            FROM payments p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN products pr ON pr.id = p.product_id
            WHERE p.id = ?
            """,
            (payment_id,),
        )
        return dict(row) if row else None

    async def get_user_payment_by_id(self, tg_user_id: int, payment_id: int) -> dict[str, Any] | None:
        row = await self._fetchone(
            """
            SELECT p.*, u.tg_id, u.username, u.full_name, u.language_code, pr.title AS product_title
                   , pr.title_i18n AS product_title_i18n
            FROM payments p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN products pr ON pr.id = p.product_id
            WHERE p.id = ? AND u.tg_id = ?
            """,
            (payment_id, tg_user_id),
        )
        return dict(row) if row else None

    async def attach_cryptobot_invoice(self, payment_id: int, invoice: dict[str, Any]) -> dict[str, Any]:
        await self.db.execute(
            """
            UPDATE payments
            SET provider_invoice_id = ?,
                provider_invoice_url = ?,
                provider_status = ?,
                merchant_id = ?,
                external_amount = ?,
                status = CASE
                    WHEN ? = 'paid' THEN 'pending'
                    ELSE status
                END,
                error_text = NULL,
                updated_at = ?,
                expires_at = COALESCE(?, expires_at),
                last_checked_at = ?
            WHERE id = ?
            """,
            (
                invoice.get("invoice_id"),
                invoice.get("bot_invoice_url") or invoice.get("mini_app_invoice_url") or invoice.get("web_app_invoice_url"),
                invoice.get("status", "active"),
                None,
                str(invoice.get("amount", "")),
                invoice.get("status", "active"),
                utcnow_iso(),
                parse_datetime_to_iso(invoice.get("expiration_date")),
                utcnow_iso(),
                payment_id,
            ),
        )
        await self.db.commit()
        payment = await self.get_payment_by_id(payment_id)
        if invoice.get("status") == "paid":
            result = await self.apply_cryptobot_invoice(invoice)
            return result.get("payment") or payment or {}
        return payment or {}

    async def attach_heleket_invoice(self, payment_id: int, invoice: dict[str, Any]) -> dict[str, Any]:
        status = self._heleket_status(invoice)
        await self.db.execute(
            """
            UPDATE payments
            SET provider_invoice_id = ?,
                provider_invoice_url = ?,
                provider_status = ?,
                merchant_id = NULL,
                external_amount = ?,
                error_text = NULL,
                updated_at = ?,
                expires_at = COALESCE(?, expires_at),
                last_checked_at = ?
            WHERE id = ?
            """,
            (
                invoice.get("uuid"),
                invoice.get("url"),
                status,
                self._heleket_external_amount(invoice),
                utcnow_iso(),
                epoch_to_iso(invoice.get("expired_at")),
                utcnow_iso(),
                payment_id,
            ),
        )
        await self.db.commit()
        payment = await self.get_payment_by_id(payment_id)
        if status in {"paid", "paid_over"}:
            result = await self.apply_heleket_invoice(invoice)
            return result.get("payment") or payment or {}
        return payment or {}

    async def attach_lolzteam_invoice(self, payment_id: int, invoice: dict[str, Any]) -> dict[str, Any]:
        await self.db.execute(
            """
            UPDATE payments
            SET provider_invoice_id = ?,
                provider_invoice_url = ?,
                provider_status = ?,
                merchant_id = ?,
                external_amount = ?,
                error_text = NULL,
                updated_at = ?,
                expires_at = COALESCE(?, expires_at),
                last_checked_at = ?
            WHERE id = ?
            """,
            (
                invoice.get("invoice_id"),
                invoice.get("url"),
                invoice.get("status", "not_paid"),
                invoice.get("merchant_id"),
                str(invoice.get("amount", "")),
                utcnow_iso(),
                epoch_to_iso(invoice.get("expires_at")),
                utcnow_iso(),
                payment_id,
            ),
        )
        await self.db.commit()
        payment = await self.get_payment_by_id(payment_id)
        if invoice.get("status") == "paid":
            result = await self.apply_lolzteam_invoice(invoice)
            return result.get("payment") or payment or {}
        return payment or {}

    async def attach_platega_invoice(self, payment_id: int, invoice: dict[str, Any], *, invoice_lifetime_minutes: int) -> dict[str, Any]:
        fallback_expires_at = utcnow() + timedelta(minutes=max(invoice_lifetime_minutes, 1))
        expires_at_iso = (
            parse_datetime_to_iso(invoice.get("expiresAt"))
            or duration_to_expires_at_iso(invoice.get("expiresIn"))
            or fallback_expires_at.replace(microsecond=0).isoformat()
        )
        invoice_url = invoice.get("redirect") or invoice.get("url")
        status = str(invoice.get("status") or "PENDING").upper()
        await self.db.execute(
            """
            UPDATE payments
            SET provider_invoice_id = ?,
                provider_invoice_url = ?,
                provider_status = ?,
                merchant_id = NULL,
                external_amount = ?,
                error_text = NULL,
                updated_at = ?,
                expires_at = COALESCE(?, expires_at),
                last_checked_at = ?
            WHERE id = ?
            """,
            (
                invoice.get("transactionId"),
                invoice_url,
                status,
                self._platega_external_amount(invoice),
                utcnow_iso(),
                expires_at_iso,
                utcnow_iso(),
                payment_id,
            ),
        )
        await self.db.commit()
        payment = await self.get_payment_by_id(payment_id)
        if status == "CONFIRMED":
            result = await self.apply_platega_invoice(invoice, invoice_lifetime_minutes=invoice_lifetime_minutes)
            return result.get("payment") or payment or {}
        return payment or {}

    async def mark_payment_failed(self, payment_id: int, error_text: str, *, release_reservation: bool) -> None:
        await self.db.execute("BEGIN IMMEDIATE")
        try:
            payment = await self._fetchone("SELECT * FROM payments WHERE id = ?", (payment_id,))
            if payment is None:
                return
            await self.db.execute(
                """
                UPDATE payments
                SET status = 'failed',
                    error_text = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (error_text, utcnow_iso(), payment_id),
            )
            if release_reservation and payment["reserved_stock_item_id"]:
                await self._release_reserved_stock_locked(int(payment["reserved_stock_item_id"]), payment["provider_payment_id"])
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

    async def list_pending_payments(self, payment_type: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = await self._fetchall(
            """
            SELECT *
            FROM payments
            WHERE payment_type = ?
              AND status = 'pending'
            ORDER BY COALESCE(last_checked_at, created_at) ASC
            LIMIT ?
            """,
            (payment_type, limit),
        )
        return [dict(row) for row in rows]

    async def apply_cryptobot_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        provider_invoice_id = invoice.get("invoice_id")
        if not provider_invoice_id:
            raise ValueError("Invoice invoice_id is missing")
        await self.db.execute("BEGIN IMMEDIATE")
        try:
            payment_row = await self._fetchone(
                "SELECT * FROM payments WHERE provider_invoice_id = ?",
                (provider_invoice_id,),
            )
            if payment_row is None:
                raise ValueError("Payment not found for invoice")
            payment = dict(payment_row)
            if payment["status"] == "completed":
                user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
                order = None
                if payment["order_id"]:
                    order = await self.get_order(payment["user_id"], payment["order_id"])
                await self.db.rollback()
                return {"action": "already_completed", "payment": payment, "user": dict(user) if user else {}, "order": order}

            expires_at_iso = parse_datetime_to_iso(invoice.get("expiration_date")) or payment.get("expires_at")
            await self.db.execute(
                """
                UPDATE payments
                SET provider_invoice_id = COALESCE(?, provider_invoice_id),
                    provider_invoice_url = COALESCE(?, provider_invoice_url),
                    provider_status = ?,
                    merchant_id = COALESCE(?, merchant_id),
                    external_amount = ?,
                    updated_at = ?,
                    expires_at = COALESCE(?, expires_at),
                    last_checked_at = ?
                WHERE id = ?
                """,
                (
                    invoice.get("invoice_id"),
                    invoice.get("bot_invoice_url") or invoice.get("mini_app_invoice_url") or invoice.get("web_app_invoice_url"),
                    invoice.get("status", "active"),
                    None,
                    str(invoice.get("amount", "")),
                    utcnow_iso(),
                    expires_at_iso,
                    utcnow_iso(),
                    payment["id"],
                ),
            )
            payment["provider_status"] = invoice.get("status", "active")
            payment["provider_invoice_id"] = invoice.get("invoice_id") or payment.get("provider_invoice_id")
            payment["provider_invoice_url"] = (
                invoice.get("bot_invoice_url")
                or invoice.get("mini_app_invoice_url")
                or invoice.get("web_app_invoice_url")
                or payment.get("provider_invoice_url")
            )
            payment["external_amount"] = str(invoice.get("amount", "")) or payment.get("external_amount")
            payment["expires_at"] = expires_at_iso

            if invoice.get("status") == "paid":
                result = await self._complete_paid_payment_locked(payment)
                await self.db.commit()
                return result

            now_iso = utcnow_iso()
            if expires_at_iso and expires_at_iso <= now_iso:
                await self.db.execute(
                    """
                    UPDATE payments
                    SET status = 'expired',
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (utcnow_iso(), payment["id"]),
                )
                if payment.get("reserved_stock_item_id"):
                    await self._release_reserved_stock_locked(int(payment["reserved_stock_item_id"]), payment["provider_payment_id"])
                payment["status"] = "expired"
                user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
                await self.db.commit()
                return {"action": "expired", "payment": payment, "user": dict(user) if user else {}, "order": None}

            await self.db.execute(
                "UPDATE payments SET status = 'pending', updated_at = ? WHERE id = ?",
                (utcnow_iso(), payment["id"]),
            )
            payment["status"] = "pending"
            user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
            await self.db.commit()
            return {"action": "pending", "payment": payment, "user": dict(user) if user else {}, "order": None}
        except Exception:
            await self.db.rollback()
            raise

    async def apply_heleket_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        provider_invoice_id = str(invoice.get("uuid") or "").strip()
        provider_payment_id = str(invoice.get("order_id") or "").strip()
        if not provider_invoice_id and not provider_payment_id:
            raise ValueError("Heleket invoice identifiers are missing")
        await self.db.execute("BEGIN IMMEDIATE")
        try:
            if provider_invoice_id:
                payment_row = await self._fetchone(
                    "SELECT * FROM payments WHERE provider_invoice_id = ?",
                    (provider_invoice_id,),
                )
            else:
                payment_row = None
            if payment_row is None and provider_payment_id:
                payment_row = await self._fetchone(
                    "SELECT * FROM payments WHERE provider_payment_id = ?",
                    (provider_payment_id,),
                )
            if payment_row is None:
                raise ValueError("Payment not found for invoice")
            payment = dict(payment_row)
            if payment["status"] == "completed":
                user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
                order = None
                if payment["order_id"]:
                    order = await self.get_order(payment["user_id"], payment["order_id"])
                await self.db.rollback()
                return {"action": "already_completed", "payment": payment, "user": dict(user) if user else {}, "order": order}

            status = self._heleket_status(invoice)
            expires_at_iso = epoch_to_iso(invoice.get("expired_at")) or payment.get("expires_at")
            await self.db.execute(
                """
                UPDATE payments
                SET provider_invoice_id = COALESCE(?, provider_invoice_id),
                    provider_invoice_url = COALESCE(?, provider_invoice_url),
                    provider_status = ?,
                    external_amount = ?,
                    updated_at = ?,
                    expires_at = COALESCE(?, expires_at),
                    last_checked_at = ?
                WHERE id = ?
                """,
                (
                    provider_invoice_id or None,
                    invoice.get("url"),
                    status,
                    self._heleket_external_amount(invoice),
                    utcnow_iso(),
                    expires_at_iso,
                    utcnow_iso(),
                    payment["id"],
                ),
            )
            payment["provider_status"] = status
            payment["provider_invoice_id"] = provider_invoice_id or payment.get("provider_invoice_id")
            payment["provider_payment_id"] = provider_payment_id or payment.get("provider_payment_id")
            payment["provider_invoice_url"] = invoice.get("url") or payment.get("provider_invoice_url")
            payment["external_amount"] = self._heleket_external_amount(invoice)
            payment["expires_at"] = expires_at_iso

            if status in {"paid", "paid_over"}:
                result = await self._complete_paid_payment_locked(payment)
                await self.db.commit()
                return result

            now_iso = utcnow_iso()
            if self._heleket_is_terminal(invoice) or (expires_at_iso and expires_at_iso <= now_iso):
                await self.db.execute(
                    """
                    UPDATE payments
                    SET status = 'expired',
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (utcnow_iso(), payment["id"]),
                )
                if payment.get("reserved_stock_item_id"):
                    await self._release_reserved_stock_locked(int(payment["reserved_stock_item_id"]), payment["provider_payment_id"])
                payment["status"] = "expired"
                user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
                await self.db.commit()
                return {"action": "expired", "payment": payment, "user": dict(user) if user else {}, "order": None}

            await self.db.execute(
                "UPDATE payments SET status = 'pending', updated_at = ? WHERE id = ?",
                (utcnow_iso(), payment["id"]),
            )
            payment["status"] = "pending"
            user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
            await self.db.commit()
            return {"action": "pending", "payment": payment, "user": dict(user) if user else {}, "order": None}
        except Exception:
            await self.db.rollback()
            raise

    async def apply_lolzteam_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        provider_invoice_id = invoice.get("invoice_id")
        provider_payment_id = invoice.get("payment_id")
        if not provider_invoice_id and not provider_payment_id:
            raise ValueError("Lolzteam invoice identifiers are missing")
        await self.db.execute("BEGIN IMMEDIATE")
        try:
            if provider_invoice_id:
                payment_row = await self._fetchone(
                    "SELECT * FROM payments WHERE provider_invoice_id = ?",
                    (provider_invoice_id,),
                )
            else:
                payment_row = await self._fetchone(
                    "SELECT * FROM payments WHERE provider_payment_id = ?",
                    (provider_payment_id,),
                )
            if payment_row is None:
                raise ValueError("Payment not found for invoice")
            payment = dict(payment_row)
            if payment["status"] == "completed":
                user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
                order = None
                if payment["order_id"]:
                    order = await self.get_order(payment["user_id"], payment["order_id"])
                await self.db.rollback()
                return {"action": "already_completed", "payment": payment, "user": dict(user) if user else {}, "order": order}

            expires_at_iso = epoch_to_iso(invoice.get("expires_at")) or payment.get("expires_at")
            await self.db.execute(
                """
                UPDATE payments
                SET provider_invoice_id = COALESCE(?, provider_invoice_id),
                    provider_invoice_url = COALESCE(?, provider_invoice_url),
                    provider_status = ?,
                    merchant_id = COALESCE(?, merchant_id),
                    external_amount = ?,
                    updated_at = ?,
                    expires_at = COALESCE(?, expires_at),
                    last_checked_at = ?
                WHERE id = ?
                """,
                (
                    invoice.get("invoice_id"),
                    invoice.get("url"),
                    invoice.get("status", "not_paid"),
                    invoice.get("merchant_id"),
                    str(invoice.get("amount", "")),
                    utcnow_iso(),
                    expires_at_iso,
                    utcnow_iso(),
                    payment["id"],
                ),
            )
            payment["provider_status"] = invoice.get("status", "not_paid")
            payment["provider_invoice_id"] = invoice.get("invoice_id") or payment.get("provider_invoice_id")
            payment["provider_invoice_url"] = invoice.get("url") or payment.get("provider_invoice_url")
            payment["provider_payment_id"] = invoice.get("payment_id") or payment.get("provider_payment_id")
            payment["external_amount"] = str(invoice.get("amount", "")) or payment.get("external_amount")
            payment["expires_at"] = expires_at_iso

            if invoice.get("status") == "paid":
                result = await self._complete_paid_payment_locked(payment)
                await self.db.commit()
                return result

            now_iso = utcnow_iso()
            if expires_at_iso and expires_at_iso <= now_iso:
                await self.db.execute(
                    """
                    UPDATE payments
                    SET status = 'expired',
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (utcnow_iso(), payment["id"]),
                )
                if payment.get("reserved_stock_item_id"):
                    await self._release_reserved_stock_locked(int(payment["reserved_stock_item_id"]), payment["provider_payment_id"])
                payment["status"] = "expired"
                user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
                await self.db.commit()
                return {"action": "expired", "payment": payment, "user": dict(user) if user else {}, "order": None}

            await self.db.execute(
                "UPDATE payments SET status = 'pending', updated_at = ? WHERE id = ?",
                (utcnow_iso(), payment["id"]),
            )
            payment["status"] = "pending"
            user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
            await self.db.commit()
            return {"action": "pending", "payment": payment, "user": dict(user) if user else {}, "order": None}
        except Exception:
            await self.db.rollback()
            raise

    async def apply_platega_invoice(self, invoice: dict[str, Any], *, invoice_lifetime_minutes: int) -> dict[str, Any]:
        provider_invoice_id = str(invoice.get("transactionId") or invoice.get("id") or "").strip()
        if not provider_invoice_id:
            raise ValueError("Platega transaction id is missing")
        await self.db.execute("BEGIN IMMEDIATE")
        try:
            payment_row = await self._fetchone(
                "SELECT * FROM payments WHERE provider_invoice_id = ? OR provider_payment_id = ?",
                (provider_invoice_id, provider_invoice_id),
            )
            if payment_row is None:
                raise ValueError("Payment not found for invoice")
            payment = dict(payment_row)
            if payment["status"] == "completed":
                user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
                order = None
                if payment["order_id"]:
                    order = await self.get_order(payment["user_id"], payment["order_id"])
                await self.db.rollback()
                return {"action": "already_completed", "payment": payment, "user": dict(user) if user else {}, "order": order}

            fallback_expires_at = utcnow() + timedelta(minutes=max(invoice_lifetime_minutes, 1))
            expires_at_iso = (
                parse_datetime_to_iso(invoice.get("expiresAt"))
                or duration_to_expires_at_iso(invoice.get("expiresIn"))
                or payment.get("expires_at")
                or fallback_expires_at.replace(microsecond=0).isoformat()
            )
            status = str(invoice.get("status") or "PENDING").upper()
            invoice_url = invoice.get("redirect") or invoice.get("url")
            await self.db.execute(
                """
                UPDATE payments
                SET provider_invoice_id = COALESCE(?, provider_invoice_id),
                    provider_invoice_url = COALESCE(?, provider_invoice_url),
                    provider_status = ?,
                    external_amount = ?,
                    updated_at = ?,
                    expires_at = COALESCE(?, expires_at),
                    last_checked_at = ?
                WHERE id = ?
                """,
                (
                    provider_invoice_id,
                    invoice_url,
                    status,
                    self._platega_external_amount(invoice),
                    utcnow_iso(),
                    expires_at_iso,
                    utcnow_iso(),
                    payment["id"],
                ),
            )
            payment["provider_status"] = status
            payment["provider_invoice_id"] = provider_invoice_id
            payment["provider_payment_id"] = payment.get("provider_payment_id") or provider_invoice_id
            payment["provider_invoice_url"] = invoice_url or payment.get("provider_invoice_url")
            payment["external_amount"] = self._platega_external_amount(invoice)
            payment["expires_at"] = expires_at_iso

            if status == "CONFIRMED":
                result = await self._complete_paid_payment_locked(payment)
                await self.db.commit()
                return result

            now_iso = utcnow_iso()
            if status in {"EXPIRED", "CANCELED", "FAILED", "CHARGEBACKED"} or (expires_at_iso and expires_at_iso <= now_iso):
                await self.db.execute(
                    """
                    UPDATE payments
                    SET status = 'expired',
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (utcnow_iso(), payment["id"]),
                )
                if payment.get("reserved_stock_item_id"):
                    await self._release_reserved_stock_locked(int(payment["reserved_stock_item_id"]), payment["provider_payment_id"])
                payment["status"] = "expired"
                user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
                await self.db.commit()
                return {"action": "expired", "payment": payment, "user": dict(user) if user else {}, "order": None}

            await self.db.execute(
                "UPDATE payments SET status = 'pending', updated_at = ? WHERE id = ?",
                (utcnow_iso(), payment["id"]),
            )
            payment["status"] = "pending"
            user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
            await self.db.commit()
            return {"action": "pending", "payment": payment, "user": dict(user) if user else {}, "order": None}
        except Exception:
            await self.db.rollback()
            raise

    async def mark_payment_expired_if_due(self, payment_id: int) -> dict[str, Any] | None:
        await self.db.execute("BEGIN IMMEDIATE")
        try:
            payment_row = await self._fetchone("SELECT * FROM payments WHERE id = ?", (payment_id,))
            if payment_row is None:
                await self.db.rollback()
                return None
            payment = dict(payment_row)
            if payment["status"] != "pending" or not payment.get("expires_at") or payment["expires_at"] > utcnow_iso():
                await self.db.rollback()
                return None
            await self.db.execute(
                "UPDATE payments SET status = 'expired', updated_at = ? WHERE id = ?",
                (utcnow_iso(), payment_id),
            )
            if payment.get("reserved_stock_item_id"):
                await self._release_reserved_stock_locked(int(payment["reserved_stock_item_id"]), payment["provider_payment_id"])
            payment["status"] = "expired"
            user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
            await self.db.commit()
            return {"action": "expired", "payment": payment, "user": dict(user) if user else {}, "order": None}
        except Exception:
            await self.db.rollback()
            raise

    @staticmethod
    def _platega_external_amount(invoice: dict[str, Any]) -> str:
        payment_details = invoice.get("paymentDetails")
        if isinstance(payment_details, dict):
            amount = payment_details.get("amount")
            currency = payment_details.get("currency")
            if amount is not None and currency:
                return f"{amount} {currency}"
        if isinstance(payment_details, str) and payment_details.strip():
            return payment_details.strip()
        amount = invoice.get("amount")
        currency = invoice.get("currency")
        if amount is not None and currency:
            return f"{amount} {currency}"
        return str(amount or "")

    @staticmethod
    def _heleket_status(invoice: dict[str, Any]) -> str:
        return str(invoice.get("payment_status") or invoice.get("status") or "check").strip().lower()

    @classmethod
    def _heleket_is_terminal(cls, invoice: dict[str, Any]) -> bool:
        status = cls._heleket_status(invoice)
        if status in {"paid", "paid_over"}:
            return False
        if status in {
            "wrong_amount",
            "fail",
            "cancel",
            "system_fail",
            "refund_process",
            "refund_fail",
            "refund_paid",
            "locked",
        }:
            return True
        return bool(invoice.get("is_final"))

    @classmethod
    def _heleket_external_amount(cls, invoice: dict[str, Any]) -> str:
        payer_amount = invoice.get("payer_amount")
        payer_currency = invoice.get("payer_currency")
        if payer_amount is not None and payer_currency:
            return f"{payer_amount} {payer_currency}"
        payment_amount = invoice.get("payment_amount")
        currency = invoice.get("currency")
        if payment_amount is not None and currency:
            return f"{payment_amount} {currency}"
        amount = invoice.get("amount")
        if amount is not None and currency:
            return f"{amount} {currency}"
        return str(invoice.get("uuid") or invoice.get("order_id") or "")

    async def _complete_paid_payment_locked(self, payment: dict[str, Any]) -> dict[str, Any]:
        user_row = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
        if user_row is None:
            raise ValueError("User not found")
        user = dict(user_row)
        if payment["purpose"] == "deposit":
            await self.db.execute(
                """
                UPDATE users
                SET balance_cents = balance_cents + ?,
                    total_deposited_cents = total_deposited_cents + ?
                WHERE id = ?
                """,
                (payment["amount_cents"], payment["amount_cents"], payment["user_id"]),
            )
            await self._apply_referral_reward_locked(payment["user_id"], payment["amount_cents"], "deposit", payment["id"])
            await self.db.execute(
                """
                UPDATE payments
                SET status = 'completed',
                    processed_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (utcnow_iso(), utcnow_iso(), payment["id"]),
            )
            updated_user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
            payment["status"] = "completed"
            return {"action": "completed", "payment": payment, "user": dict(updated_user) if updated_user else user, "order": None}

        stock_item_id = payment.get("reserved_stock_item_id")
        if not stock_item_id:
            await self.db.execute(
                "UPDATE payments SET status = 'paid_unfulfilled', processed_at = ?, updated_at = ? WHERE id = ?",
                (utcnow_iso(), utcnow_iso(), payment["id"]),
            )
            payment["status"] = "paid_unfulfilled"
            return {"action": "paid_unfulfilled", "payment": payment, "user": user, "order": None}

        stock_item = await self._fetchone("SELECT * FROM stock_items WHERE id = ?", (stock_item_id,))
        product = await self._fetchone("SELECT * FROM products WHERE id = ?", (payment["product_id"],))
        if stock_item is None or product is None:
            await self.db.execute(
                "UPDATE payments SET status = 'paid_unfulfilled', processed_at = ?, updated_at = ? WHERE id = ?",
                (utcnow_iso(), utcnow_iso(), payment["id"]),
            )
            payment["status"] = "paid_unfulfilled"
            return {"action": "paid_unfulfilled", "payment": payment, "user": user, "order": None}

        order_cursor = await self.db.execute(
            """
            INSERT INTO orders(
                user_id, product_id, stock_item_id, amount_cents, status,
                payment_method, payment_status, created_at, completed_at, payload_json
            ) VALUES(?, ?, ?, ?, 'completed', ?, 'paid', ?, ?, ?)
            """,
            (
                payment["user_id"],
                payment["product_id"],
                stock_item_id,
                payment["amount_cents"],
                payment["payment_type"],
                utcnow_iso(),
                utcnow_iso(),
                json.dumps({"payment_id": payment["id"], "provider_payment_id": payment["provider_payment_id"]}),
            ),
        )
        order_id = order_cursor.lastrowid
        await self.db.execute(
            """
            UPDATE stock_items
            SET status = 'sold',
                order_id = ?,
                sold_at = ?,
                reserved_payment_id = NULL,
                reserved_until = NULL
            WHERE id = ?
            """,
            (order_id, utcnow_iso(), stock_item_id),
        )
        await self.db.execute(
            """
            UPDATE users
            SET total_spent_cents = total_spent_cents + ?
            WHERE id = ?
            """,
            (payment["amount_cents"], payment["user_id"]),
        )
        await self._apply_referral_reward_locked(payment["user_id"], payment["amount_cents"], "purchase", order_id)
        await self.db.execute(
            """
            UPDATE payments
            SET status = 'completed',
                order_id = ?,
                processed_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (order_id, utcnow_iso(), utcnow_iso(), payment["id"]),
        )
        payment["status"] = "completed"
        payment["order_id"] = order_id
        order = await self.get_order(payment["user_id"], order_id)
        updated_user = await self._fetchone("SELECT * FROM users WHERE id = ?", (payment["user_id"],))
        return {"action": "completed", "payment": payment, "user": dict(updated_user) if updated_user else user, "order": order}

    async def _release_reserved_stock_locked(self, stock_item_id: int, provider_payment_id: str | None) -> None:
        if provider_payment_id:
            await self.db.execute(
                """
                UPDATE stock_items
                SET status = 'available',
                    reserved_payment_id = NULL,
                    reserved_until = NULL
                WHERE id = ? AND reserved_payment_id = ? AND status = 'reserved'
                """,
                (stock_item_id, provider_payment_id),
            )
            return
        await self.db.execute(
            """
            UPDATE stock_items
            SET status = 'available',
                reserved_payment_id = NULL,
                reserved_until = NULL
            WHERE id = ? AND status = 'reserved'
            """,
            (stock_item_id,),
        )

    async def purchase_with_balance(self, user_id: int, product_id: int) -> dict[str, Any]:
        await self.release_expired_reservations()
        await self.db.execute("BEGIN IMMEDIATE")
        try:
            user = await self._fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
            product = await self._fetchone("SELECT * FROM products WHERE id = ?", (product_id,))
            if user is None or product is None or product["is_active"] != 1:
                raise ValueError("Product is unavailable")
            stock_item = await self._fetchone(
                """
                SELECT * FROM stock_items
                WHERE product_id = ? AND status = 'available'
                ORDER BY id ASC
                LIMIT 1
                """,
                (product_id,),
            )
            if stock_item is None:
                raise ValueError("Out of stock")
            if user["balance_cents"] < product["price_cents"]:
                raise ValueError("Insufficient balance")
            order_cursor = await self.db.execute(
                """
                INSERT INTO orders(
                    user_id, product_id, stock_item_id, amount_cents, status,
                    payment_method, payment_status, created_at, completed_at, payload_json
                ) VALUES(?, ?, ?, ?, 'completed', 'balance', 'paid', ?, ?, '{}')
                """,
                (user_id, product_id, stock_item["id"], product["price_cents"], utcnow_iso(), utcnow_iso()),
            )
            order_id = order_cursor.lastrowid
            await self.db.execute(
                "UPDATE stock_items SET status = 'sold', order_id = ?, sold_at = ? WHERE id = ?",
                (order_id, utcnow_iso(), stock_item["id"]),
            )
            await self.db.execute(
                """
                UPDATE users
                SET balance_cents = balance_cents - ?,
                    total_spent_cents = total_spent_cents + ?
                WHERE id = ?
                """,
                (product["price_cents"], product["price_cents"], user_id),
            )
            await self._apply_referral_reward_locked(user_id, product["price_cents"], "purchase", order_id)
            await self.db.commit()
            order = await self.get_order(user_id, order_id)
            return order or {}
        except Exception:
            await self.db.rollback()
            raise

    async def payout_referral_balance(self, user_id: int) -> int:
        await self.db.execute("BEGIN IMMEDIATE")
        try:
            user = await self._fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
            if user is None:
                raise ValueError("User not found")
            amount = user["referral_balance_cents"]
            if amount <= 0:
                raise ValueError("No referral balance available")
            await self.db.execute(
                """
                UPDATE users
                SET balance_cents = balance_cents + ?,
                    referral_balance_cents = 0
                WHERE id = ?
                """,
                (amount, user_id),
            )
            await self.db.commit()
            return amount
        except Exception:
            await self.db.rollback()
            raise

    async def admin_add_balance(self, tg_id: int, amount_cents: int) -> dict[str, Any]:
        await self.db.execute("BEGIN IMMEDIATE")
        try:
            user = await self._fetchone("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
            if user is None:
                raise ValueError("User not found")
            await self.db.execute(
                """
                UPDATE users
                SET balance_cents = balance_cents + ?,
                    total_deposited_cents = total_deposited_cents + ?
                WHERE tg_id = ?
                """,
                (amount_cents, amount_cents, tg_id),
            )
            await self.db.commit()
            updated = await self.get_user_by_tg_id(tg_id)
            return updated or {}
        except Exception:
            await self.db.rollback()
            raise

    async def get_recent_orders(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = await self._fetchall(
            """
            SELECT o.*, p.title AS product_title, u.tg_id AS buyer_tg_id, u.full_name AS buyer_name
            FROM orders o
            JOIN products p ON p.id = o.product_id
            JOIN users u ON u.id = o.user_id
            ORDER BY o.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in rows]

    async def get_recent_payments(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = await self._fetchall(
            """
            SELECT p.*, u.tg_id AS buyer_tg_id, u.full_name AS buyer_name, pr.title AS product_title
            FROM payments p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN products pr ON pr.id = p.product_id
            ORDER BY p.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in rows]

    async def get_dashboard_timeseries(self, days: int = 7) -> list[dict[str, Any]]:
        rows = await self._fetchall(
            """
            SELECT substr(created_at, 1, 10) AS day,
                   COUNT(*) AS orders_count,
                   COALESCE(SUM(amount_cents), 0) AS revenue_cents
            FROM orders
            WHERE status = 'completed'
              AND substr(created_at, 1, 10) >= substr(?, 1, 10)
            GROUP BY substr(created_at, 1, 10)
            ORDER BY day ASC
            """,
            ((utcnow() - timedelta(days=max(days - 1, 0))).isoformat(),),
        )
        return [dict(row) for row in rows]

    async def get_dashboard_stats(self) -> dict[str, Any]:
        today = utcnow().date().isoformat()
        queries = {
            "users_total": "SELECT COUNT(*) AS count FROM users",
            "orders_total": "SELECT COUNT(*) AS count FROM orders WHERE status = 'completed'",
            "revenue_total": "SELECT COALESCE(SUM(amount_cents), 0) AS amount FROM orders WHERE status = 'completed'",
            "orders_today": "SELECT COUNT(*) AS count FROM orders WHERE status = 'completed' AND substr(created_at, 1, 10) = ?",
            "revenue_today": "SELECT COALESCE(SUM(amount_cents), 0) AS amount FROM orders WHERE status = 'completed' AND substr(created_at, 1, 10) = ?",
            "stock_total": "SELECT COUNT(*) AS count FROM stock_items WHERE status = 'available'",
            "products_total": "SELECT COUNT(*) AS count FROM products",
            "payments_pending_total": "SELECT COUNT(*) AS count FROM payments WHERE status = 'pending'",
            "payment_errors_total": "SELECT COUNT(*) AS count FROM payments WHERE status IN ('failed', 'paid_unfulfilled')",
        }
        stats: dict[str, Any] = {}
        for key, query in queries.items():
            params: tuple[Any, ...] = (today,) if "?" in query else ()
            row = await self._fetchone(query, params)
            stats[key] = row["amount"] if "amount" in row.keys() else row["count"]
        return stats

    async def get_dashboard_active_buyers(self, limit: int = 5) -> list[dict[str, Any]]:
        rows = await self._fetchall(
            """
            SELECT u.id,
                   u.tg_id,
                   u.username,
                   u.full_name,
                   COUNT(o.id) AS orders_count,
                   COALESCE(SUM(o.amount_cents), 0) AS total_spent_cents,
                   MAX(o.created_at) AS last_order_at
            FROM users u
            JOIN orders o ON o.user_id = u.id
            WHERE o.status = 'completed'
            GROUP BY u.id
            ORDER BY last_order_at DESC, orders_count DESC, total_spent_cents DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in rows]

    async def _apply_referral_reward_locked(
        self,
        referred_user_id: int,
        source_amount_cents: int,
        source_type: str,
        source_id: int,
    ) -> None:
        referred_user = await self._fetchone("SELECT * FROM users WHERE id = ?", (referred_user_id,))
        if referred_user is None or referred_user["referrer_user_id"] is None:
            return
        percent = int(await self.get_setting("referral_reward_percent", "2"))
        reward_cents = round(source_amount_cents * percent / 100)
        if reward_cents <= 0:
            return
        duplicate = await self._fetchone(
            """
            SELECT id FROM referral_transactions
            WHERE referred_user_id = ? AND source_type = ? AND source_id = ?
            """,
            (referred_user_id, source_type, source_id),
        )
        if duplicate:
            return
        referrer_id = referred_user["referrer_user_id"]
        await self.db.execute(
            """
            INSERT INTO referral_transactions(
                referrer_user_id, referred_user_id, amount_cents, reward_percent,
                source_type, source_id, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (referrer_id, referred_user_id, reward_cents, percent, source_type, source_id, utcnow_iso()),
        )
        await self.db.execute(
            """
            UPDATE users
            SET referral_earned_cents = referral_earned_cents + ?,
                referral_balance_cents = referral_balance_cents + ?
            WHERE id = ?
            """,
            (reward_cents, reward_cents, referrer_id),
        )

    async def _unique_slug(self, table_name: str, title: str) -> str:
        base = "".join(char.lower() if char.isalnum() else "-" for char in title).strip("-") or "item"
        slug = base
        suffix = 2
        while True:
            row = await self._fetchone(f"SELECT id FROM {table_name} WHERE slug = ?", (slug,))
            if row is None:
                return slug
            slug = f"{base}-{suffix}"
            suffix += 1
