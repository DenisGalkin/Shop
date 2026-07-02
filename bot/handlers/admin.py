from __future__ import annotations

from aiogram import Bot, F, Router, html
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.keyboards.common import (
    admin_categories_kb,
    admin_category_detail_kb,
    admin_home_kb,
    admin_product_detail_kb,
    admin_products_kb,
    admin_settings_kb,
    admin_user_detail_kb,
    admin_user_lookup_kb,
    restock_notification_kb,
)
from bot.storage.repository import ShopRepository
from bot.utils.formatting import format_date, format_money, parse_money_to_cents
from bot.utils.i18n import tr
from bot.utils.messages import render_message
from bot.utils.premium_emoji import category_premium_emoji, premium_emoji

router = Router()


class AdminStates(StatesGroup):
    add_category_title = State()
    add_category_description = State()
    add_category_emoji = State()
    add_product_title = State()
    add_product_price = State()
    add_product_description = State()
    add_product_important = State()
    add_product_warranty = State()
    edit_category_emoji = State()
    edit_product_field = State()
    add_stock = State()
    find_user = State()
    add_user_balance = State()
    edit_setting = State()


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


async def _ensure_admin_access(source: Message | CallbackQuery, config: Config) -> bool:
    user_id = source.from_user.id if isinstance(source, CallbackQuery) else source.from_user.id
    if _is_admin(user_id, config):
        return True
    if isinstance(source, CallbackQuery):
        await source.answer("Недостаточно прав", show_alert=True)
    else:
        await source.answer("Недостаточно прав")
    return False


async def _render_admin_home(target: Message | CallbackQuery, repo: ShopRepository) -> None:
    stats = await repo.get_dashboard_stats()
    text = (
        "<b>🛠 Админ-панель</b>\n\n"
        f"👥 Пользователей: {stats['users_total']}\n"
        f"🧾 Успешных заказов: {stats['orders_total']}\n"
        f"💵 Выручка: {format_money(stats['revenue_total'])}\n"
        f"🔑 Ключей на складе: {stats['stock_total']}\n"
        f"📦 Товаров: {stats['products_total']}"
    )
    await render_message(target, text, reply_markup=admin_home_kb())


async def _render_admin_category_detail(
    target: Message | CallbackQuery, repo: ShopRepository, category_id: int
) -> None:
    category = await repo.get_category(category_id)
    if not category:
        raise ValueError("Category not found")
    current_emoji_id = (category.get("premium_emoji_id") or "").strip()
    text = (
        f"<b>Категория: {html.quote(category['title'])}</b>\n\n"
        f"Emoji: {category_premium_emoji(category)}\n"
        f"Emoji ID: <code>{html.quote(current_emoji_id or '—')}</code>\n"
        f"Описание: {html.quote(category['description'] or '—')}\n"
        f"Статус: {'активна' if category['is_active'] else 'отключена'}"
    )
    await render_message(target, text, reply_markup=admin_category_detail_kb(category_id, bool(category["is_active"])))


def _extract_custom_emoji_id(message: Message) -> str | None:
    entities = [*(message.entities or ()), *(message.caption_entities or ())]
    for entity in entities:
        entity_type = getattr(entity, "type", None)
        normalized_type = getattr(entity_type, "value", entity_type)
        custom_emoji_id = getattr(entity, "custom_emoji_id", None)
        if normalized_type == "custom_emoji" and custom_emoji_id:
            return str(custom_emoji_id)
    return None


def _parse_category_emoji_input(message: Message) -> str | None:
    custom_emoji_id = _extract_custom_emoji_id(message)
    if custom_emoji_id:
        return custom_emoji_id
    text = (message.text or "").strip()
    if text in {"", "-", "—", "none", "None", "нет", "Нет"}:
        return None
    if text.isdigit():
        return text
    raise ValueError("Отправьте один premium emoji, его ID цифрами или '-' чтобы очистить поле.")


@router.message(Command("admin"))
async def admin_entry(message: Message, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(message, config):
        return
    await _render_admin_home(message, repo)


@router.callback_query(F.data == "admin:home")
async def admin_home(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    await _render_admin_home(callback, repo)


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    await _render_admin_home(callback, repo)


@router.callback_query(F.data == "admin:catalog")
async def admin_catalog(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    categories = await repo.list_categories(only_active=False)
    text = "<b>🛍 Управление ассортиментом</b>\n\nВыберите категорию для просмотра и редактирования."
    await render_message(callback, text, reply_markup=admin_categories_kb(categories, mode="catalog"))


@router.callback_query(F.data == "admin:stock")
async def admin_stock(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    categories = await repo.list_categories(only_active=False)
    text = "<b>🔑 Пополнение склада</b>\n\nВыберите категорию, затем товар, в который нужно загрузить ключи."
    await render_message(callback, text, reply_markup=admin_categories_kb(categories, mode="stock"))


@router.callback_query(F.data.startswith("admin:catalog:cat:"))
async def admin_category_detail(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    category_id = int(callback.data.split(":")[3])
    if not await repo.get_category(category_id):
        await callback.answer("Категория не найдена", show_alert=True)
        return
    await _render_admin_category_detail(callback, repo, category_id)


@router.callback_query(F.data.startswith("admin:stock:cat:"))
async def admin_stock_category(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    category_id = int(callback.data.split(":")[3])
    products = await repo.list_products(category_id, only_active=False)
    await render_message(
        callback,
        "<b>🔑 Выберите товар для пополнения склада</b>",
        reply_markup=admin_products_kb(products, category_id, mode="stock"),
    )


@router.callback_query(F.data.startswith("admin:category:products:"))
async def admin_category_products(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    category_id = int(callback.data.split(":")[3])
    products = await repo.list_products(category_id, only_active=False)
    await render_message(
        callback,
        "<b>📦 Товары категории</b>",
        reply_markup=admin_products_kb(products, category_id, mode="catalog"),
    )


@router.callback_query(F.data == "admin:category:add")
async def admin_category_add_start(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    await state.set_state(AdminStates.add_category_title)
    await render_message(callback, "Введите название новой категории:")


@router.message(AdminStates.add_category_title)
async def admin_category_add_title(message: Message, state: FSMContext, config: Config) -> None:
    if not await _ensure_admin_access(message, config):
        return
    await state.update_data(category_title=message.text.strip())
    await state.set_state(AdminStates.add_category_description)
    await message.answer("Теперь отправьте описание категории.")


@router.message(AdminStates.add_category_description)
async def admin_category_add_description(
    message: Message, state: FSMContext, repo: ShopRepository, config: Config
) -> None:
    if not await _ensure_admin_access(message, config):
        return
    await state.update_data(category_description=message.text.strip())
    await state.set_state(AdminStates.add_category_emoji)
    await message.answer(
        "Теперь отправьте premium emoji для категории одним сообщением.\n"
        "Можно также отправить ID цифрами или '-' чтобы пропустить."
    )


@router.message(AdminStates.add_category_emoji)
async def admin_category_add_emoji(
    message: Message, state: FSMContext, repo: ShopRepository, config: Config
) -> None:
    if not await _ensure_admin_access(message, config):
        return
    try:
        premium_emoji_id = _parse_category_emoji_input(message)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    data = await state.get_data()
    await repo.create_category(data["category_title"], data["category_description"], premium_emoji_id)
    await state.clear()
    await message.answer("Категория добавлена.")
    await _render_admin_home(message, repo)


@router.callback_query(F.data.startswith("admin:category:toggle:"))
async def admin_category_toggle(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    category_id = int(callback.data.split(":")[3])
    await repo.toggle_category(category_id)
    await callback.answer("Статус категории обновлён")
    await _render_admin_category_detail(callback, repo, category_id)


@router.callback_query(F.data.startswith("admin:category:emoji:"))
async def admin_category_emoji_start(callback: CallbackQuery, state: FSMContext, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    category_id = int(callback.data.split(":")[3])
    category = await repo.get_category(category_id)
    if not category:
        await callback.answer("Категория не найдена", show_alert=True)
        return
    await state.update_data(edit_category_id=category_id)
    await state.set_state(AdminStates.edit_category_emoji)
    await render_message(
        callback,
        (
            f"Отправьте новый premium emoji для категории <b>{html.quote(category['title'])}</b>.\n\n"
            "Я сам определю его ID и сохраню.\n"
            "Можно также отправить ID цифрами или '-' чтобы очистить поле."
        ),
    )


@router.message(AdminStates.edit_category_emoji)
async def admin_category_emoji_save(
    message: Message, state: FSMContext, repo: ShopRepository, config: Config
) -> None:
    if not await _ensure_admin_access(message, config):
        return
    try:
        premium_emoji_id = _parse_category_emoji_input(message)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    data = await state.get_data()
    category_id = int(data["edit_category_id"])
    category = await repo.get_category(category_id)
    if not category:
        await state.clear()
        await message.answer("Категория не найдена.")
        return
    await repo.update_category(
        category_id,
        category["title"],
        category["description"] or "",
        int(category["sort_order"]),
        premium_emoji_id,
    )
    await state.clear()
    await message.answer("Emoji категории обновлён.")
    await _render_admin_category_detail(message, repo, category_id)


@router.callback_query(F.data.startswith("admin:product:add:"))
async def admin_product_add_start(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    category_id = int(callback.data.split(":")[3])
    await state.update_data(product_category_id=category_id)
    await state.set_state(AdminStates.add_product_title)
    await render_message(callback, "Введите название товара.")


@router.message(AdminStates.add_product_title)
async def admin_product_add_title(message: Message, state: FSMContext, config: Config) -> None:
    if not await _ensure_admin_access(message, config):
        return
    await state.update_data(product_title=message.text.strip())
    await state.set_state(AdminStates.add_product_price)
    await message.answer("Введите цену в $, например 80 или 80.00")


@router.message(AdminStates.add_product_price)
async def admin_product_add_price(message: Message, state: FSMContext, config: Config) -> None:
    if not await _ensure_admin_access(message, config):
        return
    try:
        price_cents = parse_money_to_cents(message.text)
    except ValueError:
        await message.answer("Введите корректную цену.")
        return
    await state.update_data(product_price_cents=price_cents)
    await state.set_state(AdminStates.add_product_description)
    await message.answer("Отправьте описание товара.")


@router.message(AdminStates.add_product_description)
async def admin_product_add_description(message: Message, state: FSMContext, config: Config) -> None:
    if not await _ensure_admin_access(message, config):
        return
    await state.update_data(product_description=message.text.strip())
    await state.set_state(AdminStates.add_product_important)
    await message.answer("Отправьте важную информацию по товару.")


@router.message(AdminStates.add_product_important)
async def admin_product_add_important(message: Message, state: FSMContext, config: Config) -> None:
    if not await _ensure_admin_access(message, config):
        return
    await state.update_data(product_important=message.text.strip())
    await state.set_state(AdminStates.add_product_warranty)
    await message.answer("Укажите подпись гарантии, например: No Warranty")


@router.message(AdminStates.add_product_warranty)
async def admin_product_add_warranty(
    message: Message, state: FSMContext, repo: ShopRepository, config: Config
) -> None:
    if not await _ensure_admin_access(message, config):
        return
    data = await state.get_data()
    product_id = await repo.create_product(
        category_id=data["product_category_id"],
        title=data["product_title"],
        price_cents=data["product_price_cents"],
        description=data["product_description"],
        important_info=data["product_important"],
        warranty_label=message.text.strip(),
    )
    await state.clear()
    await message.answer(f"Товар создан. ID: {product_id}")
    await _render_admin_home(message, repo)


@router.callback_query(F.data.startswith("admin:catalog:product:"))
@router.callback_query(F.data.startswith("admin:stock:product:"))
async def admin_product_detail(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    parts = callback.data.split(":")
    mode = parts[1]
    product_id = int(parts[3])
    product = await repo.get_product(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return
    text = (
        f"<b>{html.quote(product['title'])}</b>\n\n"
        f"Категория: {html.quote(product['category_title'])}\n"
        f"Цена: {format_money(product['price_cents'])}\n"
        f"На складе: {product['stock_count']} шт.\n"
        f"Статус: {'активен' if product['is_active'] else 'отключен'}\n"
        f"Гарантия: {html.quote(product['warranty_label'] or '—')}\n\n"
        f"Описание:\n{html.quote(product['description'])}\n\n"
        f"Важная информация:\n{html.quote(product['important_info'])}"
    )
    await render_message(callback, text, reply_markup=admin_product_detail_kb(product_id, from_mode=mode))


@router.callback_query(F.data.startswith("admin:catalog:product_back:"))
@router.callback_query(F.data.startswith("admin:stock:product_back:"))
async def admin_product_back(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    parts = callback.data.split(":")
    mode = parts[1]
    product_id = int(parts[3])
    product = await repo.get_product(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return
    products = await repo.list_products(product["category_id"], only_active=False)
    await render_message(
        callback,
        "<b>📦 Товары категории</b>" if mode == "catalog" else "<b>🔑 Выберите товар для пополнения склада</b>",
        reply_markup=admin_products_kb(products, product["category_id"], mode=mode),
    )


@router.callback_query(F.data.startswith("admin:product:toggle:"))
async def admin_product_toggle(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    product_id = int(callback.data.split(":")[3])
    await repo.toggle_product(product_id)
    await callback.answer("Статус товара обновлён")
    product = await repo.get_product(product_id)
    if not product:
        return
    text = (
        f"<b>{html.quote(product['title'])}</b>\n\n"
        f"Категория: {html.quote(product['category_title'])}\n"
        f"Цена: {format_money(product['price_cents'])}\n"
        f"На складе: {product['stock_count']} шт.\n"
        f"Статус: {'активен' if product['is_active'] else 'отключен'}"
    )
    await render_message(callback, text, reply_markup=admin_product_detail_kb(product_id))


@router.callback_query(F.data.startswith("admin:product:edit:"))
async def admin_product_edit_start(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    _, _, _, product_id_raw, field = callback.data.split(":")
    await state.update_data(edit_product_id=int(product_id_raw), edit_field=field)
    await state.set_state(AdminStates.edit_product_field)
    prompts = {
        "title": "Отправьте новое название товара.",
        "price": "Отправьте новую цену в $.",
        "description": "Отправьте новое описание товара.",
        "important": "Отправьте новый блок важной информации.",
        "warranty": "Отправьте новое значение гарантии.",
    }
    await render_message(callback, prompts[field])


@router.message(AdminStates.edit_product_field)
async def admin_product_edit_save(
    message: Message, state: FSMContext, repo: ShopRepository, config: Config
) -> None:
    if not await _ensure_admin_access(message, config):
        return
    data = await state.get_data()
    field = data["edit_field"]
    product_id = data["edit_product_id"]
    field_map = {
        "title": "title",
        "price": "price_cents",
        "description": "description",
        "important": "important_info",
        "warranty": "warranty_label",
    }
    value: str | int = message.text.strip()
    if field == "price":
        try:
            value = parse_money_to_cents(message.text)
        except ValueError:
            await message.answer("Введите корректную цену.")
            return
    await repo.update_product_field(product_id, field_map[field], value)
    await state.clear()
    await message.answer("Товар обновлён.")
    await _render_admin_home(message, repo)


@router.callback_query(F.data.startswith("admin:stock:add:"))
async def admin_stock_add_start(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    product_id = int(callback.data.split(":")[3])
    await state.update_data(stock_product_id=product_id)
    await state.set_state(AdminStates.add_stock)
    await render_message(
        callback,
        "Отправьте ключи одним сообщением, по одному на строку. Дубликаты будут пропущены.",
    )


@router.message(AdminStates.add_stock)
async def admin_stock_add_finish(
    message: Message, state: FSMContext, repo: ShopRepository, config: Config, bot: Bot
) -> None:
    if not await _ensure_admin_access(message, config):
        return
    data = await state.get_data()
    product_id = data["stock_product_id"]
    stock_before = await repo.get_available_stock_count(product_id)
    keys = [line.strip() for line in message.text.splitlines() if line.strip()]
    added, skipped = await repo.add_stock_items(product_id, keys)
    await state.clear()
    if stock_before == 0 and added > 0:
        product = await repo.get_product(product_id)
        if product:
            recipients = await repo.get_stock_notification_recipients(product_id)
            for recipient in recipients:
                try:
                    await bot.send_message(
                        recipient["tg_id"],
                        tr(
                            recipient.get("language_code"),
                            "restock_notification_text",
                            stock_emoji=premium_emoji("stock"),
                            product_title=html.quote(product["title"]),
                        ),
                        reply_markup=restock_notification_kb(product_id, recipient.get("language_code", "ru")),
                    )
                except Exception:
                    continue
    await message.answer(f"Склад пополнен. Добавлено: {added}, пропущено дубликатов: {skipped}.")
    await _render_admin_home(message, repo)


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    await render_message(callback, "<b>👤 Работа с пользователями</b>", reply_markup=admin_user_lookup_kb())


@router.callback_query(F.data == "admin:user:find")
async def admin_user_find_start(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    await state.set_state(AdminStates.find_user)
    await render_message(callback, "Отправьте Telegram ID пользователя.")


@router.message(AdminStates.find_user)
async def admin_user_find_finish(
    message: Message, state: FSMContext, repo: ShopRepository, config: Config
) -> None:
    if not await _ensure_admin_access(message, config):
        return
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("Нужен числовой Telegram ID.")
        return
    user = await repo.get_user_by_tg_id(tg_id)
    await state.clear()
    if not user:
        await message.answer("Пользователь не найден.")
        return
    stats = await repo.get_user_stats(user["id"])
    text = (
        f"<b>{html.quote(user['full_name'])}</b>\n\n"
        f"TG ID: <code>{user['tg_id']}</code>\n"
        f"Username: @{html.quote(user['username'] or '—')}\n"
        f"Баланс: {format_money(user['balance_cents'])}\n"
        f"Всего пополнено: {format_money(user['total_deposited_cents'])}\n"
        f"Потрачено: {format_money(user['total_spent_cents'])}\n"
        f"Покупок: {stats['purchases_count']}\n"
        f"Регистрация: {format_date(user['created_at'])}"
    )
    await render_message(message, text, reply_markup=admin_user_detail_kb(tg_id))


@router.callback_query(F.data.startswith("admin:user:add_balance:"))
async def admin_user_add_balance_start(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    tg_id = int(callback.data.split(":")[3])
    await state.update_data(balance_target_tg_id=tg_id)
    await state.set_state(AdminStates.add_user_balance)
    await render_message(callback, "Введите сумму пополнения в $.")


@router.message(AdminStates.add_user_balance)
async def admin_user_add_balance_finish(
    message: Message, state: FSMContext, repo: ShopRepository, config: Config
) -> None:
    if not await _ensure_admin_access(message, config):
        return
    try:
        amount_cents = parse_money_to_cents(message.text)
    except ValueError:
        await message.answer("Введите корректную сумму.")
        return
    data = await state.get_data()
    await state.clear()
    try:
        user = await repo.admin_add_balance(data["balance_target_tg_id"], amount_cents)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await message.answer(
        f"Баланс пользователя <code>{user['tg_id']}</code> пополнен на {format_money(amount_cents)}."
    )


@router.callback_query(F.data == "admin:orders")
async def admin_orders(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    orders = await repo.get_recent_orders()
    if not orders:
        text = "<b>🧾 Заказы</b>\n\nПока нет завершённых заказов."
    else:
        lines = ["<b>🧾 Последние заказы</b>\n"]
        for order in orders:
            lines.append(
                f"#{order['id']} | {html.quote(order['product_title'])} | "
                f"{format_money(order['amount_cents'])} | {order['buyer_name']} ({order['buyer_tg_id']}) | "
                f"{format_date(order['created_at'])}"
            )
        text = "\n".join(lines)
    await render_message(callback, text, reply_markup=admin_home_kb())


@router.callback_query(F.data == "admin:settings")
async def admin_settings(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    settings = await repo.get_settings()
    text = (
        "<b>⚙️ Настройки</b>\n\n"
        f"Поддержка: @{html.quote(settings.get('support_username', 'support'))}\n"
        f"Реферальный процент: {html.quote(settings.get('referral_reward_percent', '2'))}%\n"
        f"Username бота: @{html.quote(settings.get('bot_username', '')) or '—'}"
    )
    await render_message(callback, text, reply_markup=admin_settings_kb())


@router.callback_query(F.data.startswith("admin:settings:edit_"))
async def admin_settings_edit_start(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not await _ensure_admin_access(callback, config):
        return
    setting_key = callback.data.split("edit_")[1]
    setting_map = {
        "support": ("support_username", "Отправьте username поддержки без https://t.me/"),
        "referral": ("referral_reward_percent", "Отправьте новый процент реферальной награды."),
        "bot_username": ("bot_username", "Отправьте username бота без @."),
    }
    db_key, prompt = setting_map[setting_key]
    await state.update_data(setting_key=db_key)
    await state.set_state(AdminStates.edit_setting)
    await render_message(callback, prompt)


@router.message(AdminStates.edit_setting)
async def admin_settings_edit_finish(
    message: Message, state: FSMContext, repo: ShopRepository, config: Config
) -> None:
    if not await _ensure_admin_access(message, config):
        return
    data = await state.get_data()
    value = message.text.strip().lstrip("@")
    await repo.set_setting(data["setting_key"], value)
    await state.clear()
    await message.answer("Настройка сохранена.")
    await _render_admin_home(message, repo)
