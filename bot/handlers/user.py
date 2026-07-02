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
    language_choice_kb,
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
from bot.utils.i18n import language_name, normalize_language_code, tr, translate_error
from bot.utils.messages import render_message
from bot.utils.premium_emoji import category_premium_emoji, premium_emoji

router = Router()


class UserStates(StatesGroup):
    waiting_deposit_amount = State()
    waiting_deposit_method = State()


def _category_emoji(category: dict) -> str:
    return category_premium_emoji(category)


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


def _user_language(user: dict | None) -> str:
    return normalize_language_code(user.get("language_code") if user else None)


async def _render_main_menu(target: Message | CallbackQuery, repo: ShopRepository, user_tg_id: int) -> None:
    user = await repo.get_user_by_tg_id(user_tg_id)
    if not user:
        raise ValueError("User not found")
    lang = _user_language(user)
    summary = await repo.get_main_menu_summary(user["id"])
    settings = await repo.get_settings()
    text = tr(
        lang,
        "main_menu",
        greeting_emoji=premium_emoji("greeting"),
        full_name=html.quote(user["full_name"]),
        catalog_emoji=premium_emoji("catalog"),
        balance_emoji=premium_emoji("balance"),
        balance=format_money(summary["balance_cents"], settings["default_currency"]),
    )
    await render_message(target, text, reply_markup=main_menu_kb(lang, settings["support_username"]))


async def _render_info_menu(target: Message | CallbackQuery, repo: ShopRepository) -> None:
    user_tg_id = target.from_user.id if isinstance(target, CallbackQuery) else target.from_user.id
    user = await repo.get_user_by_tg_id(user_tg_id)
    lang = _user_language(user)
    settings = await repo.get_settings()
    text = tr(lang, "info_menu_text")
    await render_message(target, text, reply_markup=info_menu_kb(lang, settings["support_username"]))


async def _render_cabinet(target: Message | CallbackQuery, repo: ShopRepository, user_tg_id: int) -> None:
    user = await repo.get_user_by_tg_id(user_tg_id)
    if not user:
        raise ValueError("User not found")
    lang = _user_language(user)
    stats = await repo.get_user_stats(user["id"])
    settings = await repo.get_settings()
    currency = settings["default_currency"]
    text = tr(
        lang,
        "cabinet_text",
        laptop_emoji=premium_emoji("laptop"),
        cabinet_emoji=premium_emoji("cabinet"),
        profile_id=user_tg_id,
        created_at=format_date(stats["created_at"]),
        language_name=language_name(lang, lang),
        balance_emoji=premium_emoji("balance"),
        balance=format_money(stats["balance_cents"], currency),
        deposited=format_money(stats["total_deposited_cents"], currency),
        spent=format_money(stats["total_spent_cents"], currency),
        orders_stats_emoji=premium_emoji("orders_stats"),
        orders_count=stats["purchases_count"],
    )
    await render_message(target, text, reply_markup=cabinet_kb(lang))


async def _render_language_menu(target: Message | CallbackQuery, repo: ShopRepository, user_tg_id: int) -> None:
    user = await repo.get_user_by_tg_id(user_tg_id)
    if not user:
        raise ValueError("User not found")
    lang = _user_language(user)
    text = tr(
        lang,
        "language_menu_text",
        language_emoji=premium_emoji("language"),
        language_name=language_name(lang, lang),
    )
    await render_message(
        target,
        text,
        reply_markup=language_choice_kb(source="profile", include_back=True, lang=lang),
    )


@router.message(CommandStart())
async def start_handler(message: Message, repo: ShopRepository, config: Config) -> None:
    existing_user = await repo.get_user_by_tg_id(message.from_user.id)
    await _ensure_user(message, repo, config)
    if existing_user is None:
        await render_message(
            message,
            tr("ru", "choose_language_prompt"),
            reply_markup=language_choice_kb(source="start"),
        )
        return
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
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    categories = await repo.list_categories()
    text = tr(lang, "catalog_choose_category", choose_emoji=premium_emoji("choose"))
    await render_message(callback, text, reply_markup=categories_kb(categories, lang))


@router.callback_query(F.data.startswith("catalog:cat:"))
async def catalog_category_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    category_id = int(callback.data.split(":")[2])
    category = await repo.get_category(category_id)
    if not category:
        await callback.answer(tr(lang, "category_not_found"), show_alert=True)
        return
    products = await repo.list_products(category_id)
    text = tr(
        lang,
        "catalog_choose_product",
        choose_emoji=premium_emoji("choose"),
        catalog_emoji=premium_emoji("catalog"),
        category=html.quote(category["title"]),
    )
    await render_message(callback, text, reply_markup=products_kb(products, lang, "catalog:root"))


@router.callback_query(F.data.startswith("catalog:product:"))
async def product_card_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    product_id = int(callback.data.split(":")[2])
    product = await repo.get_product(product_id)
    if not product:
        await callback.answer(tr(lang, "product_not_found"), show_alert=True)
        return
    notifications_enabled = bool(user and await repo.has_stock_notification(user["id"], product_id))
    text = tr(
        lang,
        "product_card_text",
        category_emoji=_category_emoji(product),
        internal_name=html.quote(product["internal_name"]),
        catalog_emoji=premium_emoji("catalog"),
        category_title=html.quote(product["category_title"]),
        price_emoji=premium_emoji("price"),
        price=format_money(product["price_cents"]),
        stock_emoji=premium_emoji("stock"),
        stock_count=product["stock_count"],
        description_emoji=premium_emoji("description"),
        description=html.quote(product["description"]),
        important_emoji=premium_emoji("important"),
        important_info=html.quote(product["important_info"]),
    )
    reply_markup = (
        product_card_kb(product_id, lang)
        if product["stock_count"] > 0
        else product_card_out_of_stock_kb(product_id, notifications_enabled, lang)
    )
    await render_message(callback, text, reply_markup=reply_markup)


@router.callback_query(F.data.startswith("catalog:back_product:"))
async def product_back_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    product_id = int(callback.data.split(":")[2])
    product = await repo.get_product(product_id)
    if not product:
        await callback.answer(tr(lang, "product_not_found"), show_alert=True)
        return
    products = await repo.list_products(product["category_id"])
    await render_message(
        callback,
        tr(
            lang,
            "catalog_choose_product",
            choose_emoji=premium_emoji("choose"),
            catalog_emoji=premium_emoji("catalog"),
            category=html.quote(product["category_title"]),
        ),
        reply_markup=products_kb(products, lang, "catalog:root"),
    )


@router.callback_query(F.data.startswith("buy:menu:"))
async def buy_menu_handler(callback: CallbackQuery, repo: ShopRepository, config: Config) -> None:
    product_id = int(callback.data.split(":")[2])
    product = await repo.get_product(product_id)
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    if not product or not user:
        await callback.answer(tr(lang, "data_not_found"), show_alert=True)
        return
    if product["stock_count"] <= 0:
        await callback.answer(tr(lang, "product_out_of_stock"), show_alert=True)
        await product_card_handler(callback, repo)
        return
    settings = await repo.get_settings()
    text = tr(
        lang,
        "buy_menu_text",
        order_emoji=premium_emoji("order"),
        catalog_emoji=premium_emoji("catalog"),
        product_title=html.quote(product["title"]),
        amount_emoji=premium_emoji("amount"),
        amount=format_money(product["price_cents"], settings["default_currency"]),
    )
    await render_message(
        callback,
        text,
        reply_markup=purchase_methods_kb(
            product_id,
            user["balance_cents"],
            lang,
            cryptobot_enabled=config.cryptopay_enabled,
        ),
    )


@router.callback_query(F.data.startswith("stock_notify:toggle:"))
async def stock_notify_toggle_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    product_id = int(callback.data.split(":")[2])
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    product = await repo.get_product(product_id)
    if not user or not product:
        await callback.answer(tr(lang, "data_not_found"), show_alert=True)
        return
    if product["stock_count"] > 0:
        await callback.answer(tr(lang, "product_already_in_stock"), show_alert=True)
        await product_card_handler(callback, repo)
        return
    enabled = await repo.toggle_stock_notification(user["id"], product_id)
    await callback.answer(tr(lang, "stock_notifications_enabled" if enabled else "stock_notifications_disabled"))
    await product_card_handler(callback, repo)


@router.callback_query(F.data.startswith("buy:balance:"))
async def buy_balance_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    product_id = int(callback.data.split(":")[2])
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    if not user:
        await callback.answer(tr(lang, "user_not_found"), show_alert=True)
        return
    try:
        order = await repo.purchase_with_balance(user["id"], product_id)
    except ValueError as exc:
        await callback.answer(translate_error(lang, str(exc)), show_alert=True)
        return
    text = tr(
        lang,
        "order_success_text",
        order_emoji=premium_emoji("order"),
        order_id=order["id"],
        category_emoji=_category_emoji(order),
        product_title=html.quote(order["product_title"]),
        price_emoji=premium_emoji("price"),
        amount=format_money(order["amount_cents"]),
        key_emoji=premium_emoji("key"),
        key_value=html.quote(order["key_value"]),
    )
    await render_message(callback, text, reply_markup=order_detail_kb(1, lang))


@router.callback_query(F.data.startswith("buy:crypto:"))
async def buy_crypto_handler(
    callback: CallbackQuery,
    repo: ShopRepository,
    payment_service: CryptoBotPaymentService,
) -> None:
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    product_id = int(callback.data.split(":")[2])
    product = await repo.get_product(product_id)
    if not product:
        await callback.answer(tr(lang, "product_not_found"), show_alert=True)
        return
    try:
        payment = await payment_service.create_product_invoice(callback.from_user.id, product_id)
    except ValueError as exc:
        await callback.answer(translate_error(lang, str(exc)), show_alert=True)
        return
    text = tr(
        lang,
        "invoice_created_text",
        order_emoji=premium_emoji("order"),
        category_emoji=_category_emoji(product),
        product_title=html.quote(product["title"]),
        price_emoji=premium_emoji("price"),
        amount=format_money(payment["amount_cents"]),
    )
    await render_message(
        callback,
        text,
        reply_markup=payment_invoice_kb(
            payment["id"],
            payment["provider_invoice_url"],
            lang,
            back_callback=f"catalog:product:{product_id}",
        ),
    )


@router.callback_query(F.data == "cabinet:main")
async def cabinet_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    await _render_cabinet(callback, repo, callback.from_user.id)


@router.callback_query(F.data == "language:menu")
async def language_menu_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    await _render_language_menu(callback, repo, callback.from_user.id)


@router.callback_query(F.data.startswith("lang:set:"))
async def language_set_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    _, _, language_code, source = callback.data.split(":")
    user = await repo.set_user_language(callback.from_user.id, language_code)
    lang = _user_language(user)
    await callback.answer(tr(lang, "language_changed"))
    if source == "start":
        await _render_main_menu(callback, repo, callback.from_user.id)
        return
    await _render_cabinet(callback, repo, callback.from_user.id)


@router.callback_query(F.data.startswith("orders:list:"))
async def orders_list_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    page = int(callback.data.split(":")[2])
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    if not user:
        await callback.answer(tr(lang, "user_not_found"), show_alert=True)
        return
    pagination = await repo.list_user_orders(user["id"], page)
    if not pagination.items:
        text = tr(lang, "orders_history_empty", description_emoji=premium_emoji("description"))
    else:
        text = tr(lang, "orders_history_choose", description_emoji=premium_emoji("description"))
    await render_message(callback, text, reply_markup=orders_kb(pagination, lang))


@router.callback_query(F.data.startswith("orders:view:"))
async def order_detail_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    _, _, order_id_raw, page_raw = callback.data.split(":")
    order_id = int(order_id_raw)
    page = int(page_raw)
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    if not user:
        await callback.answer(tr(lang, "user_not_found"), show_alert=True)
        return
    order = await repo.get_order(user["id"], order_id)
    if not order:
        await callback.answer(tr(lang, "order_not_found"), show_alert=True)
        return
    text = tr(
        lang,
        "order_detail_text",
        order_emoji=premium_emoji("order"),
        order_id=order["id"],
        created_at=format_date(order["created_at"]),
        category_emoji=_category_emoji(order),
        product_title=html.quote(order["product_title"]),
        price_emoji=premium_emoji("price"),
        amount=format_money(order["amount_cents"]),
        key_emoji=premium_emoji("key"),
        key_value=html.quote(order["key_value"] or "—"),
    )
    await render_message(callback, text, reply_markup=order_detail_kb(page, lang))


@router.callback_query(F.data == "deposit:start")
async def deposit_start_handler(callback: CallbackQuery, state: FSMContext, config: Config, repo: ShopRepository) -> None:
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    if not config.cryptopay_enabled:
        await callback.answer(tr(lang, "deposit_unavailable"), show_alert=True)
        return
    await state.set_state(UserStates.waiting_deposit_amount)
    text = tr(lang, "deposit_start_text", order_emoji=premium_emoji("order"))
    await render_message(callback, text, reply_markup=deposit_cancel_kb(lang))


@router.callback_query(F.data == "deposit:cancel")
async def deposit_cancel_handler(callback: CallbackQuery, state: FSMContext, repo: ShopRepository) -> None:
    await state.clear()
    await _render_cabinet(callback, repo, callback.from_user.id)


@router.message(UserStates.waiting_deposit_amount)
async def deposit_amount_handler(message: Message, state: FSMContext, config: Config, repo: ShopRepository) -> None:
    user = await repo.get_user_by_tg_id(message.from_user.id)
    lang = _user_language(user)
    try:
        amount_cents = parse_money_to_cents(message.text)
    except ValueError:
        await message.answer(tr(lang, "invalid_amount_input"))
        return
    await state.update_data(deposit_amount_cents=amount_cents)
    await state.set_state(UserStates.waiting_deposit_method)
    text = tr(
        lang,
        "deposit_amount_text",
        order_emoji=premium_emoji("order"),
        amount_emoji=premium_emoji("amount"),
        amount=format_money(amount_cents),
        choose_emoji=premium_emoji("choose"),
    )
    await render_message(message, text, reply_markup=deposit_methods_kb(lang, cryptobot_enabled=config.cryptopay_enabled))


@router.callback_query(F.data.startswith("deposit:method:"))
async def deposit_method_handler(
    callback: CallbackQuery,
    state: FSMContext,
    payment_service: CryptoBotPaymentService,
    repo: ShopRepository,
) -> None:
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    data = await state.get_data()
    amount_cents = data.get("deposit_amount_cents")
    if not amount_cents:
        await callback.answer(tr(lang, "enter_amount_first"), show_alert=True)
        return
    method = callback.data.split(":")[2]
    if method != "cryptobot":
        await callback.answer(tr(lang, "payment_method_unavailable"), show_alert=True)
        return
    try:
        payment = await payment_service.create_deposit_invoice(callback.from_user.id, amount_cents)
    except ValueError as exc:
        await callback.answer(translate_error(lang, str(exc)), show_alert=True)
        return
    await state.clear()
    text = tr(
        lang,
        "deposit_invoice_created_text",
        order_emoji=premium_emoji("order"),
        amount_emoji=premium_emoji("amount"),
        amount=format_money(amount_cents),
        stock_emoji=premium_emoji("stock"),
    )
    await render_message(
        callback,
        text,
        reply_markup=payment_invoice_kb(payment["id"], payment["provider_invoice_url"], lang, back_callback="cabinet:main"),
    )


@router.callback_query(F.data.startswith("payment:check:"))
async def payment_check_handler(
    callback: CallbackQuery,
    repo: ShopRepository,
    payment_service: CryptoBotPaymentService,
) -> None:
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    payment_id = int(callback.data.split(":")[2])
    try:
        payment = await payment_service.sync_payment_for_user(callback.from_user.id, payment_id)
    except ValueError as exc:
        await callback.answer(translate_error(lang, str(exc)), show_alert=True)
        return
    if payment["status"] == "completed":
        if payment["purpose"] == "deposit":
            await callback.answer(tr(lang, "payment_confirmed"))
            await _render_cabinet(callback, repo, callback.from_user.id)
            return
        order = await repo.get_order_by_payment_id(payment_id)
        if not order:
            await callback.answer(tr(lang, "payment_confirmed_processing"), show_alert=True)
            return
        text = tr(
            lang,
            "order_success_text",
            order_emoji=premium_emoji("order"),
            order_id=order["id"],
            category_emoji=_category_emoji(order),
            product_title=html.quote(order["product_title"]),
            price_emoji=premium_emoji("price"),
            amount=format_money(order["amount_cents"]),
            key_emoji=premium_emoji("key"),
            key_value=html.quote(order["key_value"]),
        )
        await render_message(callback, text, reply_markup=order_detail_kb(1, lang))
        return
    if payment["status"] == "expired":
        await callback.answer(tr(lang, "invoice_expired"), show_alert=True)
        text = tr(
            lang,
            "invoice_expired_text",
            important_emoji=premium_emoji("important"),
            amount_emoji=premium_emoji("amount"),
            amount=format_money(payment["amount_cents"]),
        )
        back_callback = "cabinet:main" if payment["purpose"] == "deposit" else f"catalog:product:{payment['product_id']}"
        await render_message(callback, text, reply_markup=back_kb(back_callback, lang))
        return
    text = tr(
        lang,
        "payment_pending_text",
        order_emoji=premium_emoji("order"),
        amount=format_money(payment["amount_cents"]),
    )
    back_callback = "cabinet:main" if payment["purpose"] == "deposit" else f"catalog:product:{payment['product_id']}"
    await render_message(
        callback,
        text,
        reply_markup=payment_invoice_kb(payment["id"], payment["provider_invoice_url"], lang, back_callback=back_callback),
    )


@router.callback_query(F.data == "ref:main")
async def referral_main_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    if not user:
        await callback.answer(tr(lang, "user_not_found"), show_alert=True)
        return
    stats = await repo.get_user_stats(user["id"])
    settings = await repo.get_settings()
    bot_username = settings.get("bot_username") or "your_bot"
    text = tr(
        lang,
        "referral_text",
        referral_emoji=premium_emoji("referral"),
        stats_emoji=premium_emoji("stats"),
        referrals_count=stats["referrals_count"],
        earned=format_money(stats["referral_earned_cents"]),
        available=format_money(stats["referral_balance_cents"]),
        link_emoji=premium_emoji("link"),
        referral_link=f"https://t.me/{html.quote(bot_username)}?start=ref_{callback.from_user.id}",
    )
    await render_message(callback, text, reply_markup=referral_kb(stats["referral_balance_cents"] > 0, lang))


@router.callback_query(F.data == "ref:payout")
async def referral_payout_handler(callback: CallbackQuery, repo: ShopRepository) -> None:
    user = await repo.get_user_by_tg_id(callback.from_user.id)
    lang = _user_language(user)
    if not user:
        await callback.answer(tr(lang, "user_not_found"), show_alert=True)
        return
    try:
        amount = await repo.payout_referral_balance(user["id"])
    except ValueError as exc:
        await callback.answer(translate_error(lang, str(exc)), show_alert=True)
        return
    await callback.answer(tr(lang, "referral_balance_transferred"))
    await _render_cabinet(callback, repo, callback.from_user.id)
