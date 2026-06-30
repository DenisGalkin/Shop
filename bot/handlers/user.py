from __future__ import annotations

from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.keyboards.common import (
    back_kb,
    cabinet_kb,
    categories_kb,
    deposit_cancel_kb,
    deposit_methods_kb,
    info_menu_kb,
    main_menu_kb,
    order_detail_kb,
    orders_kb,
    payment_invoice_kb,
    product_card_kb,
    product_card_out_of_stock_kb,
    products_kb,
    purchase_methods_kb,
    referral_kb,
    restock_notification_kb,
)
from bot.services.payments import CryptoBotPaymentService
from bot.storage.repository import ShopRepository
from bot.utils.formatting import format_date, format_money, parse_money_to_cents
from bot.utils.messages import render_message
from bot.utils.premium_emoji import category_emoji_name, premium_emoji

router = Router()


class UserStates(StatesGroup):
    waiting_deposit_amount = State()
    waiting_deposit_method = State()


def _category_emoji(category_slug: str | None) -> str:
    return premium_emoji(category_emoji_name(category_slug))


def _extract_referral_code(payload: str | None) -> int | None:
    if not payload or not payload.startswith("ref_"):
        return None
    try:
        return int(payload.split("_", 1)[1])
    except ValueError:
        return None


async def _ensure_user(message: Message, repo: ShopRepository, config: Config) -> dict:
    referrer_tg_id = _extract_referral_code(message.text.split(maxsplit=1)[1]) if message.text and " " in message.text else None
    return await repo.upsert_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        language_code=message.from_user.language_code,
        referrer_tg_id=referrer_tg_id,
        admin_ids=config.admin_ids,
    )


async def _render_main_menu(target: Message | CallbackQuery, repo: ShopRepository, user_tg_id: int) -> None:
    user = await repo.get_user_by_tg_id(user_tg_id)
    if not user:
        raise ValueError("User not found")
    summary = await repo.get_main_menu_summary(user["id"])
    settings = await repo.get_settings()
    text = (
        f"<b>{premium_emoji('greeting')} Приветствуем, {html.quote(user['full_name'])}!</b>\n\n"
        f"{premium_emoji('catalog')} Здесь вы можете приобрести доступы к AI-сервисам как для себя, так и для перепродажи.\n\n"
        f"{premium_emoji('balance')} Ваш баланс: <b>{format_money(summary['balance_cents'], settings['default_currency'])}</b>\n"
    )
    await render_message(target, text, reply_markup=main_menu_kb(settings["support_username"]))


async def _render_info_menu(target: Message | CallbackQuery, repo: ShopRepository) -> None:
    settings = await repo.get_settings()
    text = (
        '<b><tg-emoji emoji-id="5357315181649076022">ℹ️</tg-emoji> Информация</b>\n\n'
        "Выберите интересующий вас пункт:"
    )
    await render_message(target, text, reply_markup=info_menu_kb(settings["support_username"]))


async def _render_cabinet(target: Message | CallbackQuery, repo: ShopRepository, user_tg_id: int) -> None:
    user = await repo.get_user_by_tg_id(user_tg_id)
    if not user:
        raise ValueError("User not found")
    stats = await repo.get_user_stats(user["id"])
    settings = await repo.get_settings()
    currency = settings["default_currency"]
    text = (
        f"<b>{premium_emoji('laptop')} Личный кабинет пользователя</b>\n\n"

        f"{premium_emoji('cabinet')} Общая информация:\n"
        f"├ ID профиля: <code>{user_tg_id}</code>\n"
        f"├ Дата регистрации: {format_date(stats['created_at'])}\n"
        f"└ Язык интерфейса: Русский\n\n"
        f"{premium_emoji('balance')} Финансы и баланс:\n"
        f"├ Текущий баланс: {format_money(stats['balance_cents'], currency)}\n"
        f"├ Всего пополнено: {format_money(stats['total_deposited_cents'], currency)}\n"
        f"└ Сумма покупок: {format_money(stats['total_spent_cents'], currency)}\n\n"
        f"{premium_emoji('orders_stats')} Статистика заказов:\n"
        f"└ Успешно выполнено: {stats['purchases_count']} шт."
    )
    await render_message(target, text, reply_markup=cabinet_kb())


@router.message(CommandStart())
async def start_handler(message: Message, repo: ShopRepository, config: Config) -> None:
    await _ensure_user(message, repo, config)
    await _render_main_menu(message, repo, message.from_user.id)


@router.message(Command("menu"))
async def menu_handler(message: Message, repo: ShopRepository, config: Config) -> None:
    await _ensure_user(message, repo, config)
    await _render_main_menu(message, repo, message.from_user.id)


@router.callback_query(F.data == "nav:main")
async def nav_main_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    await _render_main_menu(callback, repo, callback.from_user.id)


@router.callback_query(F.data == "info:main")
async def info_main_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    await _render_info_menu(callback, repo)


@router.callback_query(F.data == "catalog:root")
async def catalog_root_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    categories = await repo.list_categories()
    text = f"<b>{premium_emoji('choose')} Выберите интересующую категорию:</b>"
    await render_message(callback, text, reply_markup=categories_kb(categories))


@router.callback_query(F.data.startswith("catalog:cat:"))
async def catalog_category_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    category_id = int(callback.data.split(":")[2])
    category = await repo.get_category(category_id)
    if not category:
        await callback.answer("Категория не найдена", show_alert=True)
        return
    products = await repo.list_products(category_id)
    text = f"<b>{premium_emoji('choose')} Выберите товар:</b>\n\n{premium_emoji('catalog')} Категория: {html.quote(category['title'])}"
    await render_message(callback, text, reply_markup=products_kb(products, "catalog:root"))


@router.callback_query(F.data.startswith("catalog:product:"))
async def product_card_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    product_id = int(callback.data.split(":")[2])
    product = await repo.get_product(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    notifications_enabled = bool(user and await repo.has_stock_notification(user["id"], product_id))
    text = (
        f"<b>{_category_emoji(product.get('category_slug'))} {html.quote(product['internal_name'])}</b>\n\n"
        f"{premium_emoji('catalog')} Категория: {html.quote(product['category_title'])}\n"
        f"{premium_emoji('price')} Стоимость: {format_money(product['price_cents'])}\n"
        f"{premium_emoji('stock')} В наличии: {product['stock_count']} шт.\n\n"
        f"{premium_emoji('description')} Описание товара:\n{html.quote(product['description'])}\n\n"
        f"{premium_emoji('important')} Важная информация:\n{html.quote(product['important_info'])}"
    )
    reply_markup = (
        product_card_kb(product_id)
        if product["stock_count"] > 0
        else product_card_out_of_stock_kb(product_id, notifications_enabled)
    )
    await render_message(callback, text, reply_markup=reply_markup)


@router.callback_query(F.data.startswith("catalog:back_product:"))
async def product_back_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    product_id = int(callback.data.split(":")[2])
    product = await repo.get_product(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return
    products = await repo.list_products(product["category_id"])
    await render_message(
        callback,
        f"<b>{premium_emoji('choose')} Выберите товар:</b>\n\n{premium_emoji('catalog')} Категория: {html.quote(product['category_title'])}",
        reply_markup=products_kb(products, "catalog:root"),
    )


@router.callback_query(F.data.startswith("buy:menu:"))
async def buy_menu_handler(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    product_id = int(callback.data.split(":")[2])
    product = await repo.get_product(product_id)
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    if not product or not user:
        await callback.answer("Данные не найдены", show_alert=True)
        return
    if product["stock_count"] <= 0:
        await callback.answer("Товар закончился", show_alert=True)
        await product_card_handler(callback, repo)
        return
    settings = await repo.get_settings()
    text = (
        f"<b>{premium_emoji('order')} Выбор способа оплаты</b>\n\n"
        f"{premium_emoji('catalog')} Вы приобретаете: {html.quote(product['title'])}\n"
        f"{premium_emoji('amount')} Сумма к оплате: {format_money(product['price_cents'], settings['default_currency'])}\n\n"
        "Выберите удобный метод оплаты:"
    )
    await render_message(
        callback,
        text,
        reply_markup=purchase_methods_kb(
            product_id,
            user["balance_cents"],
            cryptobot_enabled=config.cryptopay_enabled,
        ),
    )


@router.callback_query(F.data.startswith("stock_notify:toggle:"))
async def stock_notify_toggle_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    product_id = int(callback.data.split(":")[2])
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    product = await repo.get_product(product_id)
    if not user or not product:
        await callback.answer("Данные не найдены", show_alert=True)
        return
    if product["stock_count"] > 0:
        await callback.answer("Товар уже в наличии", show_alert=True)
        await product_card_handler(callback, repo)
        return
    enabled = await repo.toggle_stock_notification(user["id"], product_id)
    await callback.answer("Уведомления включены" if enabled else "Уведомления отключены")
    await product_card_handler(callback, repo)


@router.callback_query(F.data.startswith("buy:balance:"))
async def buy_balance_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    product_id = int(callback.data.split(":")[2])
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    try:
        order = await repo.purchase_with_balance(user["id"], product_id)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    text = (
        f"<b>{premium_emoji('order')} Заказ #{order['id']} успешно оформлен</b>\n\n"
        f"{_category_emoji(order.get('category_slug'))} Товар: {html.quote(order['product_title'])}\n"
        f"{premium_emoji('price')} Стоимость: {format_money(order['amount_cents'])}\n"
        f"{premium_emoji('key')} Ключ: <code>{html.quote(order['key_value'])}</code>\n\n"
        "Ключ также сохранён в разделе «Мои покупки»."
    )
    await render_message(callback, text, reply_markup=order_detail_kb(1))


@router.callback_query(F.data.startswith("buy:crypto:"))
async def buy_crypto_handler(
    callback: CallbackQuery,
    repo: ShopRepository,
    payment_service: CryptoBotPaymentService,
) -> None:
    product_id = int(callback.data.split(":")[2])
    product = await repo.get_product(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return
    try:
        payment = await payment_service.create_product_invoice(callback.from_user.id, product_id)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    text = (
        f"<b>{premium_emoji('order')} Счёт на оплату создан</b>\n\n"
        f"{_category_emoji(product.get('category_slug'))} Товар: {html.quote(product['title'])}\n"
        f"{premium_emoji('price')} Сумма: {format_money(payment['amount_cents'])}\n\n"
        "Мы зарезервировали для вас товар до окончания срока счёта. "
        "После оплаты бот автоматически выдаст ключ."
    )
    await render_message(
        callback,
        text,
        reply_markup=payment_invoice_kb(
            payment["id"],
            payment["provider_invoice_url"],
            back_callback=f"catalog:product:{product_id}",
        ),
    )


@router.callback_query(F.data == "cabinet:main")
async def cabinet_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    await _render_cabinet(callback, repo, callback.from_user.id)


@router.callback_query(F.data.startswith("orders:list:"))
async def orders_list_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    page = int(callback.data.split(":")[2])
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    pagination = await repo.list_user_orders(user["id"], page)
    if not pagination.items:
        text = f"<b>{premium_emoji('description')} История покупок</b>\n\nПока что у вас нет успешных заказов."
    else:
        text = f"<b>{premium_emoji('description')} История покупок</b>\n\nВыберите нужный заказ:"
    await render_message(callback, text, reply_markup=orders_kb(pagination))


@router.callback_query(F.data.startswith("orders:view:"))
async def order_detail_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    _, _, order_id_raw, page_raw = callback.data.split(":")
    order_id = int(order_id_raw)
    page = int(page_raw)
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    order = await repo.get_order(user["id"], order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    text = (
        f"<b>{premium_emoji('order')} Заказ #{order['id']} — {format_date(order['created_at'])}</b>\n\n"
        f"{_category_emoji(order.get('category_slug'))} Товар: {html.quote(order['product_title'])}\n"
        f"{premium_emoji('price')} Стоимость: {format_money(order['amount_cents'])}\n"
        f"{premium_emoji('key')} Ключ: <code>{html.quote(order['key_value'] or '—')}</code>"
    )
    await render_message(callback, text, reply_markup=order_detail_kb(page))


@router.callback_query(F.data == "deposit:start")
async def deposit_start_handler(callback: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not config.cryptopay_enabled:
        await callback.answer("Пополнение временно недоступно", show_alert=True)
        return
    await state.set_state(UserStates.waiting_deposit_amount)
    text = (
        f"<b>{premium_emoji('order')} Пополнение баланса</b>\n\n"
        "Введите сумму в USD, на которую вы хотите пополнить внутренний кошелёк:"
    )
    await render_message(callback, text, reply_markup=deposit_cancel_kb())


@router.callback_query(F.data == "deposit:cancel")
async def deposit_cancel_handler(callback: CallbackQuery, state: FSMContext, repo: ShopRepository) -> None:
    await state.clear()
    await _render_cabinet(callback, repo, callback.from_user.id)


@router.message(UserStates.waiting_deposit_amount)
async def deposit_amount_handler(message: Message, state: FSMContext, config: Config) -> None:
    try:
        amount_cents = parse_money_to_cents(message.text)
    except ValueError:
        await message.answer("Введите корректную сумму, например: 25 или 25.50")
        return
    await state.update_data(deposit_amount_cents=amount_cents)
    await state.set_state(UserStates.waiting_deposit_method)
    text = (
        f"<b>{premium_emoji('order')} Пополнение баланса</b>\n\n"
        f"{premium_emoji('amount')} Сумма: {format_money(amount_cents)}\n\n"
        f"{premium_emoji('choose')} Выберите способ оплаты:"
    )
    await render_message(message, text, reply_markup=deposit_methods_kb(cryptobot_enabled=config.cryptopay_enabled))


@router.callback_query(F.data.startswith("deposit:method:"))
async def deposit_method_handler(
    callback: CallbackQuery,
    state: FSMContext,
    payment_service: CryptoBotPaymentService,
) -> None:
    data = await state.get_data()
    amount_cents = data.get("deposit_amount_cents")
    if not amount_cents:
        await callback.answer("Сначала укажите сумму пополнения", show_alert=True)
        return
    method = callback.data.split(":")[2]
    if method != "cryptobot":
        await callback.answer("Метод оплаты недоступен", show_alert=True)
        return
    try:
        payment = await payment_service.create_deposit_invoice(callback.from_user.id, amount_cents)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await state.clear()
    text = (
        f"<b>{premium_emoji('order')} Счёт на пополнение создан</b>\n\n"
        f"{premium_emoji('amount')} Сумма: {format_money(amount_cents)}\n"
        f"{premium_emoji('stock')} После успешной оплаты баланс пополнится автоматически."
    )
    await render_message(
        callback,
        text,
        reply_markup=payment_invoice_kb(payment["id"], payment["provider_invoice_url"], back_callback="cabinet:main"),
    )


@router.callback_query(F.data.startswith("payment:check:"))
async def payment_check_handler(
    callback: CallbackQuery,
    repo: ShopRepository,
    payment_service: CryptoBotPaymentService,
) -> None:
    payment_id = int(callback.data.split(":")[2])
    try:
        payment = await payment_service.sync_payment_for_user(callback.from_user.id, payment_id)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    if payment["status"] == "completed":
        if payment["purpose"] == "deposit":
            await callback.answer("Платёж подтверждён")
            await _render_cabinet(callback, repo, callback.from_user.id)
            return
        order = await repo.get_order_by_payment_id(payment_id)
        if not order:
            await callback.answer("Платёж подтверждён, но выдача ещё обрабатывается", show_alert=True)
            return
        text = (
            f"<b>{premium_emoji('order')} Заказ #{order['id']} успешно оформлен</b>\n\n"
            f"{_category_emoji(order.get('category_slug'))} Товар: {html.quote(order['product_title'])}\n"
            f"{premium_emoji('price')} Стоимость: {format_money(order['amount_cents'])}\n"
            f"{_category_emoji(order.get('category_slug'))} Ключ:\n<code>{html.quote(order['key_value'])}</code>\n\n"
            "Ключ также сохранён в разделе «Мои покупки»."
        )
        await render_message(callback, text, reply_markup=order_detail_kb(1))
        return
    if payment["status"] == "expired":
        await callback.answer("Счёт истёк", show_alert=True)
        text = (
            f"<b>{premium_emoji('important')} Срок счёта истёк</b>\n\n"
            f"{premium_emoji('amount')} Сумма: {format_money(payment['amount_cents'])}\n\n"
            "Если оплата не успела пройти, создайте новый счёт."
        )
        back_callback = "cabinet:main" if payment["purpose"] == "deposit" else f"catalog:product:{payment['product_id']}"
        await render_message(callback, text, reply_markup=back_kb(back_callback))
        return
    text = (
        f"<b>{premium_emoji('order')} Платёж ещё не подтверждён</b>\n\n"
        f"Сумма: {format_money(payment['amount_cents'])}\n"
        "Если вы уже оплатили счёт, попробуйте проверить статус ещё раз через несколько секунд."
    )
    back_callback = "cabinet:main" if payment["purpose"] == "deposit" else f"catalog:product:{payment['product_id']}"
    await render_message(
        callback,
        text,
        reply_markup=payment_invoice_kb(payment["id"], payment["provider_invoice_url"], back_callback=back_callback),
    )


@router.callback_query(F.data == "ref:main")
async def referral_main_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    stats = await repo.get_user_stats(user["id"])
    settings = await repo.get_settings()
    bot_username = settings.get("bot_username") or "your_bot"
    text = (
        f"<b>{premium_emoji('referral')} Реферальная программа</b>\n\n"
        "Зарабатывайте, приглашая новых пользователей. Вы получаете процент с их покупок и пополнений.\n\n"
        f"{premium_emoji('stats')} Ваша статистика:\n"
        f"├ Приглашено рефералов: {stats['referrals_count']} чел.\n"
        f"├ Доход с рефералов: {format_money(stats['referral_earned_cents'])}\n"
        f"└ Доступно к выводу: {format_money(stats['referral_balance_cents'])}\n\n"
        f"{premium_emoji('link')} Ваша ссылка:\n"
        f"<code>https://t.me/{html.quote(bot_username)}?start=ref_{callback.from_user.id}</code>"
    )
    await render_message(callback, text, reply_markup=referral_kb(stats["referral_balance_cents"] > 0))


@router.callback_query(F.data == "ref:payout")
async def referral_payout_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    try:
        amount = await repo.payout_referral_balance(user["id"])
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.answer("Реферальный баланс переведён на основной")
    await _render_cabinet(callback, repo, callback.from_user.id)
