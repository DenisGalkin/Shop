from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.storage.repository import PaginationResult
from bot.utils.formatting import format_money, format_short_date
from bot.utils.i18n import tr
from bot.utils.premium_emoji import category_premium_button_icon, premium_button_icon


def language_choice_kb(*, source: str, include_back: bool = False, back_callback: str = "cabinet:main", lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇸 English", callback_data=f"lang:set:en:{source}")
    builder.button(text="🇷🇺 Русский", callback_data=f"lang:set:ru:{source}")
    builder.button(text="🇺🇦Українська", callback_data=f"lang:set:uk:{source}")
    if include_back:
        builder.button(
            text=tr(lang, "back"),
            callback_data=back_callback,
            icon_custom_emoji_id=premium_button_icon("back"),
        )
        builder.adjust(3, 1)
    else:
        builder.adjust(3)
    return builder.as_markup()


def main_menu_kb(lang: str, support_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=tr(lang, "main_menu_catalog"),
        callback_data="catalog:root",
        icon_custom_emoji_id=premium_button_icon("catalog"),
    )
    builder.button(
        text=tr(lang, "main_menu_cabinet"),
        callback_data="cabinet:main",
        icon_custom_emoji_id=premium_button_icon("cabinet"),
    )
    builder.button(
        text=tr(lang, "main_menu_info"),
        callback_data="info:main",
        icon_custom_emoji_id="5357315181649076022",
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def info_menu_kb(lang: str, support_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=tr(lang, "info_user_agreement"),
        url="https://telegra.ph/POLZOVATELSKOE-SOGLASHENIE-06-30-29",
        icon_custom_emoji_id="5395613344897979554",
    )
    builder.button(
        text=tr(lang, "info_privacy_policy"),
        url="https://telegra.ph/POLITIKA-KONFIDENCIALNOSTI-I-OBRABOTKI-DANNYH-06-30",
        icon_custom_emoji_id="5395613344897979554",
    )
    builder.button(
        text=tr(lang, "info_refund_policy"),
        url="https://telegra.ph/POLITIKA-VOZVRATA-SREDSTV-I-OBMENA-TOVARA-06-30",
        icon_custom_emoji_id="5395613344897979554",
    )
    builder.button(
        text=tr(lang, "support"),
        url=f"https://t.me/{support_username}",
        icon_custom_emoji_id=premium_button_icon("support"),
    )
    builder.button(
        text=tr(lang, "to_main_menu"),
        callback_data="nav:main",
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1)
    return builder.as_markup()


def categories_kb(categories: list[dict], lang: str, back_callback: str = "nav:main") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(
            text=category["title"],
            callback_data=f"catalog:cat:{category['id']}",
            icon_custom_emoji_id=category_premium_button_icon(category),
        )
    builder.button(
        text=tr(lang, "to_main_menu"),
        callback_data=back_callback,
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1)
    return builder.as_markup()


def products_kb(products: list[dict], lang: str, back_callback: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(
            text=f"{product['title']} — {format_money(product['price_cents'])}",
            callback_data=f"catalog:product:{product['id']}",
            icon_custom_emoji_id=category_premium_button_icon(product),
        )
    builder.button(
        text=tr(lang, "back_to_categories"),
        callback_data=back_callback,
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1)
    return builder.as_markup()


def product_card_kb(product_id: int, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=tr(lang, "place_order"),
        callback_data=f"buy:menu:{product_id}",
        icon_custom_emoji_id=premium_button_icon("order"),
    )
    builder.button(
        text=tr(lang, "back_to_list"),
        callback_data=f"catalog:back_product:{product_id}",
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1)
    return builder.as_markup()


def product_card_out_of_stock_kb(product_id: int, notifications_enabled: bool, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=tr(lang, "stop_notify") if notifications_enabled else tr(lang, "notify_on_restock"),
        callback_data=f"stock_notify:toggle:{product_id}",
        icon_custom_emoji_id=premium_button_icon("cancel" if notifications_enabled else "notify"),
    )
    builder.button(
        text=tr(lang, "back_to_list"),
        callback_data=f"catalog:back_product:{product_id}",
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1)
    return builder.as_markup()


def purchase_methods_kb(
    product_id: int,
    balance_cents: int,
    lang: str,
    *,
    heleket_enabled: bool,
    cryptobot_enabled: bool,
    lolz_enabled: bool,
    platega_enabled: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if heleket_enabled:
        builder.button(
            text="Криптовалюта" if lang != "en" else "Cryptocurrency",
            callback_data=f"buy:heleket:{product_id}",
            icon_custom_emoji_id=premium_button_icon("heleket"),
        )
    builder.button(
        text=tr(lang, "buy_balance_option", balance=format_money(balance_cents)),
        callback_data=f"buy:balance:{product_id}",
        icon_custom_emoji_id=premium_button_icon("balance"),
    )
    if cryptobot_enabled:
        builder.button(
            text="CryptoBot",
            callback_data=f"buy:crypto:{product_id}",
            icon_custom_emoji_id=premium_button_icon("cryptobot"),
        )
    if lolz_enabled:
        builder.button(
            text="Lolzteam",
            callback_data=f"buy:lolz:{product_id}",
            icon_custom_emoji_id=premium_button_icon("lolz"),
        )
    if platega_enabled:
        builder.button(
            text="СБП (+8%)" if lang != "en" else "FSP (+8%)",
            callback_data=f"buy:platega:{product_id}",
            icon_custom_emoji_id=premium_button_icon("platega"),
        )
    builder.button(
        text=tr(lang, "cancel_purchase"),
        callback_data=f"catalog:product:{product_id}",
        icon_custom_emoji_id=premium_button_icon("cancel"),
    )
    builder.adjust(1)
    return builder.as_markup()


def cabinet_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=tr(lang, "cabinet_orders"), callback_data="orders:list:1", icon_custom_emoji_id=premium_button_icon("description"))
    builder.button(text=tr(lang, "cabinet_deposit"), callback_data="deposit:start", icon_custom_emoji_id=premium_button_icon("order"))
    builder.button(text=tr(lang, "cabinet_referral"), callback_data="ref:main", icon_custom_emoji_id=premium_button_icon("referral"))
    builder.button(text=tr(lang, "cabinet_language"), callback_data="language:menu", icon_custom_emoji_id=premium_button_icon("language"))
    builder.button(text=tr(lang, "to_main_menu"), callback_data="nav:main", icon_custom_emoji_id=premium_button_icon("back"))
    builder.adjust(2, 1, 1, 1)
    return builder.as_markup()


def orders_kb(pagination: PaginationResult, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for order in pagination.items:
        builder.button(
            text=tr(
                lang,
                "orders_list_item",
                order_id=order["id"],
                amount=format_money(order["amount_cents"]),
                date=format_short_date(order["created_at"]),
            ),
            callback_data=f"orders:view:{order['id']}:{pagination.page}",
            icon_custom_emoji_id=premium_button_icon("order_item"),
        )
    if pagination.page > 1:
        builder.button(text=tr(lang, "orders_back"), callback_data=f"orders:list:{pagination.page - 1}", icon_custom_emoji_id=premium_button_icon("prev"))
    if pagination.page < pagination.pages:
        builder.button(text=tr(lang, "orders_forward"), callback_data=f"orders:list:{pagination.page + 1}", icon_custom_emoji_id=premium_button_icon("next"))
    builder.button(text=tr(lang, "orders_back_to_cabinet"), callback_data="cabinet:main", icon_custom_emoji_id=premium_button_icon("back"))
    builder.adjust(1)
    return builder.as_markup()


def order_detail_kb(page: int, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=tr(lang, "orders_to_list"), callback_data=f"orders:list:{page}", icon_custom_emoji_id=premium_button_icon("back"))
    return builder.as_markup()


def back_kb(callback_data: str, lang: str, text: str | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=text or tr(lang, "back"), callback_data=callback_data, icon_custom_emoji_id=premium_button_icon("back"))
    return builder.as_markup()


def deposit_cancel_kb(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=tr(lang, "cancel"), callback_data="deposit:cancel", icon_custom_emoji_id=premium_button_icon("cancel"))
    return builder.as_markup()


def deposit_methods_kb(
    lang: str,
    *,
    heleket_enabled: bool,
    cryptobot_enabled: bool,
    lolz_enabled: bool,
    platega_enabled: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if heleket_enabled:
        builder.button(
            text="Криптовалюта" if lang != "en" else "Cryptocurrency",
            callback_data="deposit:method:heleket",
            icon_custom_emoji_id=premium_button_icon("heleket"),
        )
    if cryptobot_enabled:
        builder.button(
            text="CryptoBot",
            callback_data="deposit:method:cryptobot",
            icon_custom_emoji_id=premium_button_icon("cryptobot"),
        )
    if lolz_enabled:
        builder.button(
            text="Lolzteam",
            callback_data="deposit:method:lolzteam",
            icon_custom_emoji_id=premium_button_icon("lolz"),
        )
    if platega_enabled:
        builder.button(
            text="СБП (+ 8%)" if lang != "en" else "FSP (+ 8%)",
            callback_data="deposit:method:platega",
            icon_custom_emoji_id=premium_button_icon("platega"),
        )
    builder.button(text=tr(lang, "cancel"), callback_data="deposit:cancel", icon_custom_emoji_id=premium_button_icon("cancel"))
    builder.adjust(1)
    return builder.as_markup()


def payment_invoice_kb(payment_id: int, payment_url: str, lang: str, *, back_callback: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=tr(lang, "pay_invoice"),
        url=payment_url,
        icon_custom_emoji_id=premium_button_icon("order"),
    )
    builder.button(
        text=tr(lang, "check_payment"),
        callback_data=f"payment:check:{payment_id}",
        icon_custom_emoji_id=premium_button_icon("refresh"),
    )
    builder.button(
        text=tr(lang, "back"),
        callback_data=back_callback,
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1)
    return builder.as_markup()


def restock_notification_kb(product_id: int, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=tr(lang, "restock_buy"),
        callback_data=f"buy:menu:{product_id}",
        icon_custom_emoji_id=premium_button_icon("order"),
    )
    builder.button(
        text=tr(lang, "restock_to_menu"),
        callback_data="nav:main",
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1, 1)
    return builder.as_markup()


def referral_kb(can_payout: bool, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_payout:
        builder.button(text=tr(lang, "withdraw_to_balance"), callback_data="ref:payout", icon_custom_emoji_id=premium_button_icon("amount"))
    builder.button(text=tr(lang, "orders_back_to_cabinet"), callback_data="cabinet:main", icon_custom_emoji_id=premium_button_icon("back"))
    builder.adjust(1)
    return builder.as_markup()


def admin_home_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.button(text="🛍 Ассортимент", callback_data="admin:catalog")
    builder.button(text="🔑 Склад", callback_data="admin:stock")
    builder.button(text="👤 Пользователи", callback_data="admin:users")
    builder.button(text="🧾 Заказы", callback_data="admin:orders")
    builder.button(text="⚙️ Настройки", callback_data="admin:settings")
    builder.adjust(2)
    return builder.as_markup()


def admin_categories_kb(categories: list[dict], mode: str = "catalog") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        prefix = "✅" if category["is_active"] else "⛔️"
        builder.button(
            text=f"{prefix} {category['title']}",
            callback_data=f"admin:{mode}:cat:{category['id']}",
            icon_custom_emoji_id=category_premium_button_icon(category),
        )
    builder.button(text="➕ Добавить категорию", callback_data="admin:category:add")
    builder.button(text="⬅️ В админку", callback_data="admin:home")
    builder.adjust(1)
    return builder.as_markup()


def admin_category_detail_kb(category_id: int, active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✨ Emoji категории", callback_data=f"admin:category:emoji:{category_id}")
    builder.button(text="📦 Товары категории", callback_data=f"admin:category:products:{category_id}")
    builder.button(text="➕ Добавить товар", callback_data=f"admin:product:add:{category_id}")
    builder.button(text="🔄 Вкл/выкл категорию", callback_data=f"admin:category:toggle:{category_id}")
    builder.button(text="⬅️ К категориям", callback_data="admin:catalog")
    builder.adjust(1)
    return builder.as_markup()


def admin_products_kb(products: list[dict], category_id: int, mode: str = "catalog") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        prefix = "✅" if product["is_active"] else "⛔️"
        builder.button(
            text=f"{prefix} {product['title']} ({product['stock_count']} шт.)",
            callback_data=f"admin:{mode}:product:{product['id']}",
        )
    if mode == "catalog":
        builder.button(text="➕ Добавить товар", callback_data=f"admin:product:add:{category_id}")
        builder.button(text="⬅️ К категориям", callback_data=f"admin:catalog:cat:{category_id}")
    else:
        builder.button(text="⬅️ К категориям", callback_data="admin:stock")
    builder.adjust(1)
    return builder.as_markup()


def admin_product_detail_kb(product_id: int, from_mode: str = "catalog") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Название", callback_data=f"admin:product:edit:{product_id}:title")
    builder.button(text="💵 Цена", callback_data=f"admin:product:edit:{product_id}:price")
    builder.button(text="📝 Описание", callback_data=f"admin:product:edit:{product_id}:description")
    builder.button(text="⚠️ Важная информация", callback_data=f"admin:product:edit:{product_id}:important")
    builder.button(text="🛡 Гарантия", callback_data=f"admin:product:edit:{product_id}:warranty")
    builder.button(text="🔄 Вкл/выкл товар", callback_data=f"admin:product:toggle:{product_id}")
    builder.button(text="🔑 Пополнить ключи", callback_data=f"admin:stock:add:{product_id}")
    builder.button(text="⬅️ Назад", callback_data=f"admin:{from_mode}:product_back:{product_id}")
    builder.adjust(1)
    return builder.as_markup()


def admin_user_lookup_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔎 Найти пользователя", callback_data="admin:user:find")
    builder.button(text="⬅️ В админку", callback_data="admin:home")
    builder.adjust(1)
    return builder.as_markup()


def admin_user_detail_kb(tg_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Пополнить баланс", callback_data=f"admin:user:add_balance:{tg_id}")
    builder.button(text="⬅️ К поиску", callback_data="admin:users")
    builder.adjust(1)
    return builder.as_markup()


def admin_settings_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Ссылка поддержки", callback_data="admin:settings:edit_support")
    builder.button(text="🤝 Реферальный процент", callback_data="admin:settings:edit_referral")
    builder.button(text="🤖 Username бота", callback_data="admin:settings:edit_bot_username")
    builder.button(text="⬅️ В админку", callback_data="admin:home")
    builder.adjust(1)
    return builder.as_markup()
