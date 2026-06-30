from __future__ import annotations

PREMIUM_EMOJI: dict[str, tuple[str, str]] = {
    "greeting": ("5438496463044752972", "👋"),
    "welcome": ("5258203794772085854", "💎"),
    "catalog": ("5836672976862319297", "🛍"),
    "balance": ("5332600543963522398", "💰"),
    "referral": ("5262668735398812646", "🤝"),
    "cabinet": ("5431874671446350745", "👤"),
    "support": ("5443038326535759644", "💬"),
    "choose": ("5406745015365943482", "🗂"),
    "claude": ("5341790816199286662", "🔑"),
    "chatgpt": ("5341790652990530125", "🤖"),
    "grok": ("5341553317392720144", "⚡"),
    "back": ("5352759161945867747", "⬅️"),
    "price": ("5197434882321567830", "💵"),
    "stock": ("5206607081334906820", "📦"),
    "description": ("5395613344897979554", "📝"),
    "important": ("5447644880824181073", "⚠️"),
    "order": ("5472250091332993630", "🧾"),
    "amount": ("5409048419211682843", "💸"),
    "cancel": ("5210952531676504517", "❌"),
    "notify": ("5242628160297641831", "🔔"),
    "profile_id": ("5390854796011906616", "🆔"),
    "date": ("5274055917766202507", "📅"),
    "language": ("5447410659077661506", "🌐"),
    "orders_stats": ("5231200819986047254", "📁"),
    "order_item": ("5359805631320571519", "🧾"),
    "prev": ("5983506750387523533", "⬅️"),
    "next": ("5386630210345003204", "➡️"),
    "cryptobot": ("5217705010539812022", "🪙"),
    "lolz": ("5251447471913057341", "💳"),
    "stats": ("5465493682574604098", "📊"),
    "link": ("5271604874419647061", "🔗"),
    "refresh": ("5433878454078556670", "🔄"),
    "laptop": ("5316688029434264397", "💻"),
    "key": ("5330115548900501467", "🔑")
}


def premium_emoji(name: str) -> str:
    emoji_id, fallback = PREMIUM_EMOJI[name]
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def premium_button_icon(name: str) -> str:
    return PREMIUM_EMOJI[name][0]


def category_emoji_name(category_slug: str | None) -> str:
    if category_slug in {"claude", "chatgpt", "grok"}:
        return category_slug
    return "stock"
