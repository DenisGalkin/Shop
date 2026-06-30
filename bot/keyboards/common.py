from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.storage.repository import PaginationResult
from bot.utils.formatting import format_money, format_short_date
from bot.utils.premium_emoji import category_emoji_name, premium_button_icon


def main_menu_kb(support_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Каталог товаров",
        callback_data="catalog:root",
        icon_custom_emoji_id=premium_button_icon("catalog"),
    )
    builder.button(
        text="Личный кабинет",
        callback_data="cabinet:main",
        icon_custom_emoji_id=premium_button_icon("cabinet"),
    )
    builder.button(
        text="Информация",
        callback_data="info:main",
        icon_custom_emoji_id="5357315181649076022",
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def info_menu_kb(support_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Пользовательское соглашение",
        url="https://telegra.ph/POLZOVATELSKOE-SOGLASHENIE-06-30-29",
        icon_custom_emoji_id="5395613344897979554",
    )
    builder.button(
        text="Политика конфиденциальности",
        url="https://telegra.ph/POLITIKA-KONFIDENCIALNOSTI-I-OBRABOTKI-DANNYH-06-30",
        icon_custom_emoji_id="5395613344897979554",
    )
    builder.button(
        text="Политика возврата",
        url="https://telegra.ph/POLITIKA-VOZVRATA-SREDSTV-I-OBMENA-TOVARA-06-30",
        icon_custom_emoji_id="5395613344897979554",
    )
    builder.button(
        text="Поддержка",
        url=f"https://t.me/{support_username}",
        icon_custom_emoji_id=premium_button_icon("support"),
    )
    builder.button(
        text="В главное меню",
        callback_data="nav:main",
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1)
    return builder.as_markup()


def categories_kb(categories: list[dict], back_callback: str = "nav:main") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        icon_name = category_emoji_name(category.get("slug"))
        builder.button(
            text=category["title"],
            callback_data=f"catalog:cat:{category['id']}",
            icon_custom_emoji_id=premium_button_icon(icon_name),
        )
    builder.button(
        text="В главное меню",
        callback_data=back_callback,
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1)
    return builder.as_markup()


def products_kb(products: list[dict], back_callback: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(
            text=f"{product['title']} — {format_money(product['price_cents'])}",
            callback_data=f"catalog:product:{product['id']}",
            icon_custom_emoji_id=premium_button_icon(category_emoji_name(product.get("category_slug"))),
        )
    builder.button(
        text="Назад в категории",
        callback_data=back_callback,
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1)
    return builder.as_markup()


def product_card_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Оформить заказ",
        callback_data=f"buy:menu:{product_id}",
        icon_custom_emoji_id=premium_button_icon("order"),
    )
    builder.button(
        text="Назад к списку",
        callback_data=f"catalog:back_product:{product_id}",
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1)
    return builder.as_markup()


def product_card_out_of_stock_kb(product_id: int, notifications_enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Не уведомлять" if notifications_enabled else "Уведомить о поступлении",
        callback_data=f"stock_notify:toggle:{product_id}",
        icon_custom_emoji_id=premium_button_icon("cancel" if notifications_enabled else "notify"),
    )
    builder.button(
        text="Назад к списку",
        callback_data=f"catalog:back_product:{product_id}",
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1)
    return builder.as_markup()


def purchase_methods_kb(product_id: int, balance_cents: int, *, cryptobot_enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"Баланс бота ({format_money(balance_cents)})",
        callback_data=f"buy:balance:{product_id}",
        icon_custom_emoji_id=premium_button_icon("balance"),
    )
    if cryptobot_enabled:
        builder.button(
            text="CryptoBot",
            callback_data=f"buy:crypto:{product_id}",
            icon_custom_emoji_id=premium_button_icon("cryptobot"),
        )
    builder.button(
        text="Отменить покупку",
        callback_data=f"catalog:product:{product_id}",
        icon_custom_emoji_id=premium_button_icon("cancel"),
    )
    builder.adjust(1)
    return builder.as_markup()


def cabinet_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Мои покупки", callback_data="orders:list:1", icon_custom_emoji_id=premium_button_icon("description"))
    builder.button(text="Пополнить", callback_data="deposit:start", icon_custom_emoji_id=premium_button_icon("order"))
    builder.button(text="Реферальная программа", callback_data="ref:main", icon_custom_emoji_id=premium_button_icon("referral"))
    builder.button(text="В главное меню", callback_data="nav:main", icon_custom_emoji_id=premium_button_icon("back"))
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def orders_kb(pagination: PaginationResult) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for order in pagination.items:
        builder.button(
            text=(
                f"Заказ #{order['id']} — "
                f"{format_money(order['amount_cents'])} ({format_short_date(order['created_at'])})"
            ),
            callback_data=f"orders:view:{order['id']}:{pagination.page}",
            icon_custom_emoji_id=premium_button_icon("order_item"),
        )
    if pagination.page > 1:
        builder.button(text="Назад", callback_data=f"orders:list:{pagination.page - 1}", icon_custom_emoji_id=premium_button_icon("prev"))
    if pagination.page < pagination.pages:
        builder.button(text="Вперед", callback_data=f"orders:list:{pagination.page + 1}", icon_custom_emoji_id=premium_button_icon("next"))
    builder.button(text="В личный кабинет", callback_data="cabinet:main", icon_custom_emoji_id=premium_button_icon("back"))
    builder.adjust(1)
    return builder.as_markup()


def order_detail_kb(page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="К списку заказов", callback_data=f"orders:list:{page}", icon_custom_emoji_id=premium_button_icon("back"))
    return builder.as_markup()


def back_kb(callback_data: str, text: str = "Назад") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=text, callback_data=callback_data, icon_custom_emoji_id=premium_button_icon("back"))
    return builder.as_markup()


def deposit_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Отмена", callback_data="deposit:cancel", icon_custom_emoji_id=premium_button_icon("cancel"))
    return builder.as_markup()


def deposit_methods_kb(*, cryptobot_enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if cryptobot_enabled:
        builder.button(
            text="CryptoBot",
            callback_data="deposit:method:cryptobot",
            icon_custom_emoji_id=premium_button_icon("cryptobot"),
        )
    builder.button(text="Отмена", callback_data="deposit:cancel", icon_custom_emoji_id=premium_button_icon("cancel"))
    builder.adjust(1)
    return builder.as_markup()


def payment_invoice_kb(payment_id: int, payment_url: str, *, back_callback: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Оплатить счет",
        url=payment_url,
        icon_custom_emoji_id=premium_button_icon("order"),
    )
    builder.button(
        text="Проверить оплату",
        callback_data=f"payment:check:{payment_id}",
        icon_custom_emoji_id=premium_button_icon("refresh"),
    )
    builder.button(
        text="Назад",
        callback_data=back_callback,
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1)
    return builder.as_markup()


def restock_notification_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Купить",
        callback_data=f"buy:menu:{product_id}",
        icon_custom_emoji_id=premium_button_icon("order"),
    )
    builder.button(
        text="В меню",
        callback_data="nav:main",
        icon_custom_emoji_id=premium_button_icon("back"),
    )
    builder.adjust(1, 1)
    return builder.as_markup()


def referral_kb(can_payout: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_payout:
        builder.button(text="Вывести на баланс", callback_data="ref:payout", icon_custom_emoji_id=premium_button_icon("amount"))
    builder.button(text="В личный кабинет", callback_data="cabinet:main", icon_custom_emoji_id=premium_button_icon("back"))
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
        builder.button(text=f"{prefix} {category['title']}", callback_data=f"admin:{mode}:cat:{category['id']}")
    builder.button(text="➕ Добавить категорию", callback_data="admin:category:add")
    builder.button(text="⬅️ В админку", callback_data="admin:home")
    builder.adjust(1)
    return builder.as_markup()


def admin_category_detail_kb(category_id: int, active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
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
