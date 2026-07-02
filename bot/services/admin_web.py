from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any

from aiohttp import web

from bot.config import Config
from bot.storage.repository import ShopRepository, utcnow
from bot.utils.formatting import format_date, format_money, parse_money_to_cents
from bot.utils.i18n import SUPPORTED_LANGUAGES, normalize_language_code, pick_localized_text


STATIC_DIR = Path(__file__).resolve().parent.parent / "webadmin" / "static"
SESSION_COOKIE = "shop_admin_session"


def _html_shell() -> str:
    return """<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Shop Admin</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="/admin/assets/admin.css?v=5" />
  </head>
  <body>
    <div id="app"></div>
    <script src="/admin/assets/admin.js?v=5" defer></script>
  </body>
</html>"""


def _sign_session(username: str, expires_at: str, secret: str) -> str:
    payload = f"{username}|{expires_at}"
    signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}|{signature}"


def _read_session_token(token: str, secret: str) -> dict[str, str] | None:
    try:
        username, expires_at, signature = token.split("|", 2)
    except ValueError:
        return None
    expected = hmac.new(secret.encode("utf-8"), f"{username}|{expires_at}".encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    if utcnow() >= datetime.fromisoformat(expires_at):
        return None
    return {"username": username, "expires_at": expires_at}


def _json_error(message: str, status: int = 400) -> web.Response:
    return web.json_response({"ok": False, "error": message}, status=status)


async def _get_json(request: web.Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise web.HTTPBadRequest(text="invalid json") from exc
    if not isinstance(payload, dict):
        raise web.HTTPBadRequest(text="invalid json")
    return payload


async def _require_admin(request: web.Request) -> dict[str, str]:
    config: Config = request.app["config"]
    token = request.cookies.get(SESSION_COOKIE, "")
    session = _read_session_token(token, config.admin_web_secret) if token else None
    if session is None:
        raise web.HTTPUnauthorized(text="unauthorized")
    return session


def _set_session_cookie(response: web.StreamResponse, request: web.Request, config: Config) -> None:
    expires_at = (utcnow() + timedelta(hours=max(config.admin_web_session_ttl_hours, 1))).isoformat()
    token = _sign_session(config.admin_web_username, expires_at, config.admin_web_secret)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=request.scheme == "https",
        samesite="Lax",
        max_age=max(config.admin_web_session_ttl_hours, 1) * 3600,
        path="/",
    )


def _clear_session_cookie(response: web.StreamResponse) -> None:
    response.del_cookie(SESSION_COOKIE, path="/")


def _serialize_order(order: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": order["id"],
        "product_title": order["product_title"],
        "buyer_name": order["buyer_name"],
        "buyer_tg_id": order["buyer_tg_id"],
        "amount_cents": order["amount_cents"],
        "amount_label": format_money(order["amount_cents"]),
        "status": order["status"],
        "payment_method": order["payment_method"],
        "created_at": order["created_at"],
        "created_label": format_date(order["created_at"]),
    }


def _serialize_payment(payment: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": payment["id"],
        "buyer_name": payment["buyer_name"],
        "buyer_tg_id": payment["buyer_tg_id"],
        "amount_cents": payment["amount_cents"],
        "amount_label": format_money(payment["amount_cents"], payment["currency"]),
        "currency": payment["currency"],
        "status": payment["status"],
        "purpose": payment["purpose"],
        "product_title": payment.get("product_title"),
        "payment_type": payment["payment_type"],
        "provider_status": payment["provider_status"],
        "created_at": payment["created_at"],
        "created_label": format_date(payment["created_at"]),
    }


def _serialize_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "tg_id": user["tg_id"],
        "username": user["username"] or "",
        "full_name": user["full_name"],
        "balance_cents": user["balance_cents"],
        "balance_label": format_money(user["balance_cents"]),
        "total_deposited_cents": user["total_deposited_cents"],
        "total_deposited_label": format_money(user["total_deposited_cents"]),
        "total_spent_cents": user["total_spent_cents"],
        "total_spent_label": format_money(user["total_spent_cents"]),
        "orders_count": user.get("orders_count", 0),
        "referral_balance_cents": user["referral_balance_cents"],
        "referral_balance_label": format_money(user["referral_balance_cents"]),
        "created_at": user["created_at"],
        "created_label": format_date(user["created_at"]),
        "is_admin": bool(user["is_admin"]),
    }


def _serialize_dashboard_buyer(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "tg_id": user["tg_id"],
        "username": user["username"] or "",
        "full_name": user["full_name"],
        "orders_count": user.get("orders_count", 0),
        "total_spent_cents": user.get("total_spent_cents", 0),
        "total_spent_label": format_money(user.get("total_spent_cents", 0)),
        "last_order_at": user.get("last_order_at"),
        "last_order_label": format_date(user.get("last_order_at")),
    }


def _serialize_category(category: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": category["id"],
        "slug": category["slug"],
        "title": category["title"],
        "description": category["description"] or "",
        "premium_emoji_id": category.get("premium_emoji_id") or "",
        "sort_order": category["sort_order"],
        "is_active": bool(category["is_active"]),
        "products_count": category.get("products_count", 0),
        "active_products_count": category.get("active_products_count", 0),
        "stock_total": category.get("stock_total", 0),
    }


def _serialize_product(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": product["id"],
        "category_id": product["category_id"],
        "category_title": product["category_title"],
        "title": product["title"],
        "title_i18n": product.get("title_i18n") or {},
        "internal_name": product["internal_name"],
        "internal_name_i18n": product.get("internal_name_i18n") or {},
        "description": product["description"],
        "description_i18n": product.get("description_i18n") or {},
        "important_info": product["important_info"],
        "important_info_i18n": product.get("important_info_i18n") or {},
        "price_cents": product["price_cents"],
        "price_label": format_money(product["price_cents"]),
        "warranty_label": product["warranty_label"],
        "sort_order": product["sort_order"],
        "stock_count": product["stock_count"],
        "sold_count": product.get("sold_count", 0),
        "is_active": bool(product["is_active"]),
    }


def _parse_localized_field(
    payload: dict[str, Any],
    field_name: str,
    *,
    fallback: str = "",
    existing: dict[str, str] | None = None,
) -> dict[str, str]:
    raw_value = payload.get(f"{field_name}_i18n")
    result: dict[str, str] = {}
    if isinstance(raw_value, dict):
        for language_code, text in raw_value.items():
            lang = normalize_language_code(str(language_code))
            value = str(text or "").strip()
            if value:
                result[lang] = value
    elif existing:
        for language_code, text in existing.items():
            lang = normalize_language_code(str(language_code))
            value = str(text or "").strip()
            if value:
                result[lang] = value
    plain_value = str(payload.get(field_name, fallback)).strip()
    if plain_value and not result.get("ru"):
        result["ru"] = plain_value
    return {lang: result.get(lang, "") for lang in SUPPORTED_LANGUAGES if result.get(lang, "").strip()}


def _primary_localized_value(values: dict[str, str], fallback: str = "") -> str:
    return pick_localized_text(values, "ru", fallback)


def _serialize_stock_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "product_id": item["product_id"],
        "key_value": item["key_value"],
        "status": item["status"],
        "order_id": item.get("order_id"),
        "reserved_payment_id": item.get("reserved_payment_id"),
        "reserved_until": item.get("reserved_until"),
        "reserved_until_label": format_date(item.get("reserved_until")),
        "created_at": item["created_at"],
        "created_label": format_date(item["created_at"]),
        "sold_at": item.get("sold_at"),
        "sold_label": format_date(item.get("sold_at")),
        "can_delete": item["status"] == "available",
    }


async def admin_shell(_: web.Request) -> web.Response:
    return web.Response(text=_html_shell(), content_type="text/html")


async def admin_session(request: web.Request) -> web.Response:
    config: Config = request.app["config"]
    token = request.cookies.get(SESSION_COOKIE, "")
    session = _read_session_token(token, config.admin_web_secret) if token else None
    if session is None:
        return web.json_response({"ok": True, "session": None, "authenticated": False})
    return web.json_response({"ok": True, "session": session, "authenticated": True})


async def admin_login(request: web.Request) -> web.Response:
    config: Config = request.app["config"]
    payload = await _get_json(request)
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not config.admin_web_enabled:
        return _json_error("ADMIN_WEB credentials are not configured", status=503)
    if not (
        hmac.compare_digest(username, config.admin_web_username)
        and hmac.compare_digest(password, config.admin_web_password)
    ):
        return _json_error("Неверный логин или пароль", status=401)
    response = web.json_response({"ok": True})
    _set_session_cookie(response, request, config)
    return response


async def admin_logout(request: web.Request) -> web.Response:
    await _require_admin(request)
    response = web.json_response({"ok": True})
    _clear_session_cookie(response)
    return response


async def admin_dashboard(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    stats = await repo.get_dashboard_stats()
    recent_orders = [*_map(_serialize_order, await repo.get_recent_orders(limit=8))]
    recent_payments = [*_map(_serialize_payment, await repo.get_recent_payments(limit=8))]
    categories = await repo.list_admin_categories()
    products = await repo.list_admin_products()
    active_buyers = await repo.get_dashboard_active_buyers(limit=5)
    timeseries_rows = await repo.get_dashboard_timeseries(days=7)
    timeseries_map = {row["day"]: row for row in timeseries_rows}
    series: list[dict[str, Any]] = []
    for day_offset in range(6, -1, -1):
        day = (utcnow() - timedelta(days=day_offset)).date().isoformat()
        row = timeseries_map.get(day, {})
        series.append(
            {
                "day": day,
                "orders_count": int(row.get("orders_count", 0)),
                "revenue_cents": int(row.get("revenue_cents", 0)),
                "revenue_label": format_money(int(row.get("revenue_cents", 0))),
            }
        )
    out_of_stock = [product for product in products if product["is_active"] and product["stock_count"] == 0]
    low_stock = [product for product in products if product["is_active"] and product["stock_count"] <= 3][:5]
    hidden_stocked_products = [product for product in products if not product["is_active"] and product["stock_count"] > 0][:5]
    empty_categories = [category for category in categories if category["products_count"] == 0][:5]
    sales_last_7_days_total = sum(item["revenue_cents"] for item in series)
    return web.json_response(
        {
            "ok": True,
            "stats": {
                **stats,
                "revenue_label": format_money(stats["revenue_total"]),
                "revenue_today_label": format_money(stats["revenue_today"]),
                "categories_total": len(categories),
                "products_without_keys_total": len(out_of_stock),
                "hidden_stocked_products_total": len([product for product in products if not product["is_active"] and product["stock_count"] > 0]),
                "categories_without_products_total": len([category for category in categories if category["products_count"] == 0]),
                "sales_last_7_days_total": sales_last_7_days_total,
                "sales_last_7_days_label": format_money(sales_last_7_days_total),
            },
            "series": series,
            "recent_orders": recent_orders,
            "recent_payments": recent_payments,
            "active_buyers": [*_map(_serialize_dashboard_buyer, active_buyers)],
            "low_stock": [*_map(_serialize_product, low_stock)],
            "out_of_stock": [*_map(_serialize_product, out_of_stock[:5])],
            "hidden_stocked_products": [*_map(_serialize_product, hidden_stocked_products)],
            "empty_categories": [*_map(_serialize_category, empty_categories)],
        }
    )


def _map(func, items):
    for item in items:
        yield func(item)


async def admin_categories(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    if request.method == "GET":
        categories = [*_map(_serialize_category, await repo.list_admin_categories())]
        return web.json_response({"ok": True, "items": categories})
    payload = await _get_json(request)
    title = str(payload.get("title", "")).strip()
    if not title:
        return _json_error("Название категории обязательно")
    description = str(payload.get("description", "")).strip()
    premium_emoji_id = str(payload.get("premium_emoji_id", "")).strip() or None
    sort_order = int(payload.get("sort_order") or 0)
    category_id = await repo.create_category(title, description, premium_emoji_id)
    await repo.update_category(category_id, title, description, sort_order, premium_emoji_id)
    category = await repo.get_category(category_id)
    return web.json_response({"ok": True, "item": _serialize_category(category or {})})


async def admin_category_update(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    category_id = int(request.match_info["category_id"])
    payload = await _get_json(request)
    category = await repo.get_category(category_id)
    if not category:
        return _json_error("Категория не найдена", status=404)
    title = str(payload.get("title", category["title"])).strip()
    if not title:
        return _json_error("Название категории обязательно")
    description = str(payload.get("description", category["description"] or "")).strip()
    premium_emoji_id = str(payload.get("premium_emoji_id", category.get("premium_emoji_id") or "")).strip() or None
    sort_order = int(payload.get("sort_order", category["sort_order"]) or 0)
    await repo.update_category(category_id, title, description, sort_order, premium_emoji_id)
    updated = await repo.get_category(category_id)
    return web.json_response({"ok": True, "item": _serialize_category(updated or {})})


async def admin_category_toggle(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    category_id = int(request.match_info["category_id"])
    await repo.toggle_category(category_id)
    category = await repo.get_category(category_id)
    return web.json_response({"ok": True, "item": _serialize_category(category or {})})


async def admin_products(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    if request.method == "GET":
        search = request.query.get("search", "")
        category_id = request.query.get("category_id")
        parsed_category_id = int(category_id) if category_id and category_id.isdigit() else None
        products = [*_map(_serialize_product, await repo.list_admin_products(search=search, category_id=parsed_category_id))]
        categories = [*_map(_serialize_category, await repo.list_admin_categories())]
        return web.json_response({"ok": True, "items": products, "categories": categories})
    payload = await _get_json(request)
    title_i18n = _parse_localized_field(payload, "title")
    internal_name_i18n = _parse_localized_field(payload, "internal_name")
    description_i18n = _parse_localized_field(payload, "description")
    important_info_i18n = _parse_localized_field(payload, "important_info")
    title = _primary_localized_value(title_i18n)
    internal_name = _primary_localized_value(internal_name_i18n, title) or title
    category_id = int(payload.get("category_id") or 0)
    if not title or not category_id:
        return _json_error("Заполните название и категорию")
    product_id = await repo.create_product(
        category_id=category_id,
        title=title,
        internal_name=internal_name,
        price_cents=parse_money_to_cents(str(payload.get("price", "0"))),
        description=_primary_localized_value(description_i18n),
        important_info=_primary_localized_value(important_info_i18n),
        warranty_label=str(payload.get("warranty_label", "")).strip(),
        title_i18n=title_i18n,
        internal_name_i18n=internal_name_i18n,
        description_i18n=description_i18n,
        important_info_i18n=important_info_i18n,
    )
    await repo.update_product(
        product_id,
        category_id=category_id,
        title=title,
        internal_name=internal_name,
        description=_primary_localized_value(description_i18n),
        important_info=_primary_localized_value(important_info_i18n),
        price_cents=parse_money_to_cents(str(payload.get("price", "0"))),
        warranty_label=str(payload.get("warranty_label", "")).strip(),
        sort_order=int(payload.get("sort_order") or 0),
        title_i18n=title_i18n,
        internal_name_i18n=internal_name_i18n,
        description_i18n=description_i18n,
        important_info_i18n=important_info_i18n,
    )
    product = await repo.get_product(product_id)
    return web.json_response({"ok": True, "item": _serialize_product(product or {})})


async def admin_product_update(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    product_id = int(request.match_info["product_id"])
    existing = await repo.get_product(product_id)
    if not existing:
        return _json_error("Товар не найден", status=404)
    payload = await _get_json(request)
    title_i18n = _parse_localized_field(payload, "title", fallback=existing["title"], existing=existing.get("title_i18n"))
    internal_name_i18n = _parse_localized_field(
        payload,
        "internal_name",
        fallback=existing["internal_name"],
        existing=existing.get("internal_name_i18n"),
    )
    description_i18n = _parse_localized_field(
        payload,
        "description",
        fallback=existing["description"],
        existing=existing.get("description_i18n"),
    )
    important_info_i18n = _parse_localized_field(
        payload,
        "important_info",
        fallback=existing["important_info"],
        existing=existing.get("important_info_i18n"),
    )
    await repo.update_product(
        product_id,
        category_id=int(payload.get("category_id", existing["category_id"])),
        title=_primary_localized_value(title_i18n, existing["title"]),
        internal_name=_primary_localized_value(internal_name_i18n, existing["internal_name"]),
        description=_primary_localized_value(description_i18n, existing["description"]),
        important_info=_primary_localized_value(important_info_i18n, existing["important_info"]),
        price_cents=parse_money_to_cents(str(payload.get("price", existing["price_cents"] / 100))),
        warranty_label=str(payload.get("warranty_label", existing["warranty_label"])).strip(),
        sort_order=int(payload.get("sort_order", existing["sort_order"]) or 0),
        title_i18n=title_i18n,
        internal_name_i18n=internal_name_i18n,
        description_i18n=description_i18n,
        important_info_i18n=important_info_i18n,
    )
    updated = await repo.get_product(product_id)
    return web.json_response({"ok": True, "item": _serialize_product(updated or {})})


async def admin_product_toggle(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    product_id = int(request.match_info["product_id"])
    await repo.toggle_product(product_id)
    product = await repo.get_product(product_id)
    return web.json_response({"ok": True, "item": _serialize_product(product or {})})


async def admin_product_stock(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    product_id = int(request.match_info["product_id"])
    product = await repo.get_product(product_id)
    if product is None:
        return _json_error("Товар не найден", status=404)
    payload = await _get_json(request)
    keys_raw = str(payload.get("keys", ""))
    keys = [line.strip() for line in keys_raw.splitlines() if line.strip()]
    if not keys:
        return _json_error("Добавьте хотя бы один ключ")
    added, skipped = await repo.add_stock_items(product_id, keys)
    product = await repo.get_product(product_id)
    return web.json_response(
        {
            "ok": True,
            "added": added,
            "skipped": skipped,
            "item": _serialize_product(product or {}),
        }
    )


async def admin_product_stock_items(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    product_id = int(request.match_info["product_id"])
    product = await repo.get_product(product_id)
    if product is None:
        return _json_error("Товар не найден", status=404)
    items = [*_map(_serialize_stock_item, await repo.list_admin_stock_items(product_id))]
    return web.json_response({"ok": True, "product": _serialize_product(product), "items": items})


async def admin_product_stock_item_delete(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    product_id = int(request.match_info["product_id"])
    stock_item_id = int(request.match_info["stock_item_id"])
    product = await repo.get_product(product_id)
    if product is None:
        return _json_error("Товар не найден", status=404)
    try:
        deleted = await repo.delete_admin_stock_item(product_id, stock_item_id)
    except ValueError as exc:
        return _json_error(str(exc), status=409)
    if not deleted:
        return _json_error("Ключ не найден", status=404)
    updated_product = await repo.get_product(product_id)
    return web.json_response({"ok": True, "item": _serialize_product(updated_product or product)})


async def admin_users(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    search = request.query.get("search", "")
    users = [*_map(_serialize_user, await repo.list_admin_users(search=search, limit=60))]
    return web.json_response({"ok": True, "items": users})


async def admin_user_balance(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    payload = await _get_json(request)
    amount_cents = parse_money_to_cents(str(payload.get("amount", "")))
    if amount_cents <= 0:
        return _json_error("Сумма должна быть больше нуля")
    tg_id = int(request.match_info["tg_id"])
    user = await repo.admin_add_balance(tg_id, amount_cents)
    return web.json_response({"ok": True, "item": _serialize_user(user), "amount_label": format_money(amount_cents)})


async def admin_orders(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    limit = min(max(int(request.query.get("limit", "25")), 1), 100)
    orders = [*_map(_serialize_order, await repo.get_recent_orders(limit=limit))]
    return web.json_response({"ok": True, "items": orders})


async def admin_payments(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    limit = min(max(int(request.query.get("limit", "25")), 1), 100)
    payments = [*_map(_serialize_payment, await repo.get_recent_payments(limit=limit))]
    return web.json_response({"ok": True, "items": payments})


async def admin_settings(request: web.Request) -> web.Response:
    await _require_admin(request)
    repo: ShopRepository = request.app["repo"]
    if request.method == "GET":
        return web.json_response({"ok": True, "item": await repo.get_settings()})
    payload = await _get_json(request)
    editable_keys = {"support_username", "bot_username", "referral_reward_percent", "default_currency"}
    updated: dict[str, str] = {}
    for key in editable_keys:
        if key in payload:
            value = str(payload[key]).strip().lstrip("@")
            if key == "default_currency":
                value = value.upper()
            await repo.set_setting(key, value)
            updated[key] = value
    return web.json_response({"ok": True, "item": {**await repo.get_settings(), **updated}})


async def admin_asset(request: web.Request) -> web.FileResponse:
    filename = request.match_info["filename"]
    if "/" in filename or "\\" in filename:
        raise web.HTTPNotFound()
    path = STATIC_DIR / filename
    if not path.exists():
        raise web.HTTPNotFound()
    return web.FileResponse(path)


def setup_admin_routes(app: web.Application) -> None:
    app.router.add_get("/admin", admin_shell)
    app.router.add_get("/admin/assets/{filename}", admin_asset)
    app.router.add_post("/admin/api/login", admin_login)
    app.router.add_post("/admin/api/logout", admin_logout)
    app.router.add_get("/admin/api/session", admin_session)
    app.router.add_get("/admin/api/dashboard", admin_dashboard)
    app.router.add_get("/admin/api/categories", admin_categories)
    app.router.add_post("/admin/api/categories", admin_categories)
    app.router.add_patch("/admin/api/categories/{category_id:\\d+}", admin_category_update)
    app.router.add_post("/admin/api/categories/{category_id:\\d+}/toggle", admin_category_toggle)
    app.router.add_get("/admin/api/products", admin_products)
    app.router.add_post("/admin/api/products", admin_products)
    app.router.add_patch("/admin/api/products/{product_id:\\d+}", admin_product_update)
    app.router.add_post("/admin/api/products/{product_id:\\d+}/toggle", admin_product_toggle)
    app.router.add_post("/admin/api/products/{product_id:\\d+}/stock", admin_product_stock)
    app.router.add_get("/admin/api/products/{product_id:\\d+}/stock-items", admin_product_stock_items)
    app.router.add_delete("/admin/api/products/{product_id:\\d+}/stock-items/{stock_item_id:\\d+}", admin_product_stock_item_delete)
    app.router.add_get("/admin/api/users", admin_users)
    app.router.add_post("/admin/api/users/{tg_id:\\d+}/balance", admin_user_balance)
    app.router.add_get("/admin/api/orders", admin_orders)
    app.router.add_get("/admin/api/payments", admin_payments)
    app.router.add_get("/admin/api/settings", admin_settings)
    app.router.add_patch("/admin/api/settings", admin_settings)
