from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def format_money(cents: int, currency: str = "USD") -> str:
    if currency in {"USD", "$"}:
        return f"${cents / 100:.2f}"
    return f"{currency} {cents / 100:.2f}"


def parse_money_to_cents(raw_value: str) -> int:
    normalized = raw_value.strip().replace(",", ".").replace("$", "")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError("Invalid amount") from exc
    cents = int((amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if cents <= 0:
        raise ValueError("Amount must be positive")
    return cents


def format_date(raw_value: str | None) -> str:
    if not raw_value:
        return "—"
    try:
        return datetime.fromisoformat(raw_value).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return raw_value


def format_short_date(raw_value: str | None) -> str:
    if not raw_value:
        return "—"
    try:
        return datetime.fromisoformat(raw_value).strftime("%d.%m.%Y")
    except ValueError:
        return raw_value
