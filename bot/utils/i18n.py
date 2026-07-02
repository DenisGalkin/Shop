from __future__ import annotations

from typing import Any


SUPPORTED_LANGUAGES = ("en", "ru", "uk")


TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        "choose_language_prompt": '{globus} Choose language / Выберите язык / Виберiть мову',
        "language_english": "English",
        "language_russian": "Русский",
        "language_ukrainian": "Українська",
        "language_changed": "Язык интерфейса обновлен",
        "main_menu": (
            "<b>{greeting_emoji} Приветствуем, {full_name}!</b>\n\n"
            "{catalog_emoji} Здесь вы можете приобрести доступы к AI-сервисам как для себя, так и для перепродажи.\n\n"
            "{balance_emoji} Ваш баланс: <b>{balance}</b>\n"
        ),
        "main_menu_catalog": "Каталог товаров",
        "main_menu_cabinet": "Личный кабинет",
        "main_menu_info": "Информация",
        "info_menu_text": "<b><tg-emoji emoji-id=\"5357315181649076022\">ℹ️</tg-emoji> Информация</b>\n\nВыберите интересующий вас пункт:",
        "info_user_agreement": "Пользовательское соглашение",
        "info_privacy_policy": "Политика конфиденциальности",
        "info_refund_policy": "Политика возврата",
        "support": "Поддержка",
        "to_main_menu": "В главное меню",
        "cabinet_text": (
            "<b>{laptop_emoji} Личный кабинет пользователя</b>\n\n"
            "{cabinet_emoji} Общая информация:\n"
            "├ ID профиля: <code>{profile_id}</code>\n"
            "├ Дата регистрации: {created_at}\n"
            "└ Язык интерфейса: {language_name}\n\n"
            "{balance_emoji} Финансы и баланс:\n"
            "├ Текущий баланс: {balance}\n"
            "├ Всего пополнено: {deposited}\n"
            "└ Сумма покупок: {spent}\n\n"
            "{orders_stats_emoji} Статистика заказов:\n"
            "└ Успешно выполнено: {orders_count} шт."
        ),
        "cabinet_orders": "Мои покупки",
        "cabinet_deposit": "Пополнить",
        "cabinet_referral": "Реферальная программа",
        "cabinet_language": "Сменить язык",
        "language_menu_text": (
            "<b>{language_emoji} Язык интерфейса</b>\n\n"
            "Текущий язык: {language_name}\n"
            "Выберите нужный вариант:"
        ),
        "catalog_choose_category": "<b>{choose_emoji} Выберите интересующую категорию:</b>",
        "catalog_choose_product": "<b>{choose_emoji} Выберите товар:</b>\n\n{catalog_emoji} Категория: {category}",
        "category_not_found": "Категория не найдена",
        "product_not_found": "Товар не найден",
        "order_not_found": "Заказ не найден",
        "data_not_found": "Данные не найдены",
        "product_out_of_stock": "Товар закончился",
        "product_already_in_stock": "Товар уже в наличии",
        "stock_notifications_enabled": "Уведомления включены",
        "stock_notifications_disabled": "Уведомления отключены",
        "product_card_text": (
            "<b>{category_emoji} {internal_name}</b>\n\n"
            "{catalog_emoji} Категория: {category_title}\n"
            "{price_emoji} Стоимость: {price}\n"
            "{stock_emoji} В наличии: {stock_count} шт.\n\n"
            "{description_emoji} Описание товара:\n{description}\n\n"
            "{important_emoji} Важная информация:\n{important_info}"
        ),
        "back_to_categories": "Назад в категории",
        "place_order": "Оформить заказ",
        "back_to_list": "Назад к списку",
        "notify_on_restock": "Уведомить о поступлении",
        "stop_notify": "Не уведомлять",
        "buy_menu_text": (
            "<b>{order_emoji} Выбор способа оплаты</b>\n\n"
            "{catalog_emoji} Вы приобретаете: {product_title}\n"
            "{amount_emoji} Сумма к оплате: {amount}\n\n"
            "Выберите удобный метод оплаты:"
        ),
        "buy_balance_option": "Баланс бота ({balance})",
        "cancel_purchase": "Отменить покупку",
        "order_success_text": (
            "<b>{order_emoji} Заказ #{order_id} успешно оформлен</b>\n\n"
            "{category_emoji} Товар: {product_title}\n"
            "{price_emoji} Стоимость: {amount}\n"
            "{key_emoji} Ключ: <code>{key_value}</code>\n\n"
            "Ключ также сохранён в разделе «Мои покупки»."
        ),
        "invoice_created_text": (
            "<b>{order_emoji} Счёт на оплату создан</b>\n\n"
            "{category_emoji} Товар: {product_title}\n"
            "{price_emoji} Сумма: {amount}\n\n"
            "Мы зарезервировали для вас товар до окончания срока счёта. После оплаты бот автоматически выдаст ключ."
        ),
        "orders_history_empty": "<b>{description_emoji} История покупок</b>\n\nПока что у вас нет успешных заказов.",
        "orders_history_choose": "<b>{description_emoji} История покупок</b>\n\nВыберите нужный заказ:",
        "orders_list_item": "Заказ #{order_id} — {amount} ({date})",
        "orders_back_to_cabinet": "В личный кабинет",
        "orders_forward": "Вперед",
        "orders_back": "Назад",
        "order_detail_text": (
            "<b>{order_emoji} Заказ #{order_id} — {created_at}</b>\n\n"
            "{category_emoji} Товар: {product_title}\n"
            "{price_emoji} Стоимость: {amount}\n"
            "{key_emoji} Ключ: <code>{key_value}</code>"
        ),
        "orders_to_list": "К списку заказов",
        "deposit_unavailable": "Пополнение временно недоступно",
        "deposit_start_text": (
            "<b>{order_emoji} Пополнение баланса</b>\n\n"
            "Введите сумму в USD, на которую вы хотите пополнить внутренний кошелёк:"
        ),
        "cancel": "Отмена",
        "invalid_amount_input": "Введите корректную сумму, например: 25 или 25.50",
        "deposit_amount_text": (
            "<b>{order_emoji} Пополнение баланса</b>\n\n"
            "{amount_emoji} Сумма: {amount}\n\n"
            "{choose_emoji} Выберите способ оплаты:"
        ),
        "enter_amount_first": "Сначала укажите сумму пополнения",
        "payment_method_unavailable": "Метод оплаты недоступен",
        "deposit_invoice_created_text": (
            "<b>{order_emoji} Счёт на пополнение создан</b>\n\n"
            "{amount_emoji} Сумма: {amount}\n"
            "{stock_emoji} После успешной оплаты баланс пополнится автоматически."
        ),
        "pay_invoice": "Оплатить счет",
        "check_payment": "Проверить оплату",
        "payment_confirmed": "Платёж подтверждён",
        "payment_confirmed_processing": "Платёж подтверждён, но выдача ещё обрабатывается",
        "invoice_expired": "Счёт истёк",
        "invoice_expired_text": (
            "<b>{important_emoji} Срок счёта истёк</b>\n\n"
            "{amount_emoji} Сумма: {amount}\n\n"
            "Если оплата не успела пройти, создайте новый счёт."
        ),
        "payment_pending_text": (
            "<b>{order_emoji} Платёж ещё не подтверждён</b>\n\n"
            "Сумма: {amount}\n"
            "Если вы уже оплатили счёт, попробуйте проверить статус ещё раз через несколько секунд."
        ),
        "referral_text": (
            "<b>{referral_emoji} Реферальная программа</b>\n\n"
            "Зарабатывайте, приглашая новых пользователей. Вы получаете процент с их покупок и пополнений.\n\n"
            "{stats_emoji} Ваша статистика:\n"
            "├ Приглашено рефералов: {referrals_count} чел.\n"
            "├ Доход с рефералов: {earned}\n"
            "└ Доступно к выводу: {available}\n\n"
            "{link_emoji} Ваша ссылка:\n"
            "<code>{referral_link}</code>"
        ),
        "withdraw_to_balance": "Вывести на баланс",
        "referral_balance_transferred": "Реферальный баланс переведён на основной",
        "back": "Назад",
        "restock_notification_text": "{stock_emoji} Товар {product_title} снова в наличии!",
        "restock_buy": "Купить",
        "restock_to_menu": "В меню",
        "crypto_deposit_description": "Пополнение баланса Telegram-магазина",
        "crypto_product_description": "Оплата товара: {product_name}",
        "crypto_deposit_hidden_message": "После оплаты вернитесь в бота: баланс пополнится автоматически.",
        "crypto_product_hidden_message": "После оплаты бот автоматически выдаст товар и сохранит покупку в истории.",
        "payment_fulfillment_issue": (
            "{important_emoji} Платёж подтверждён, но автоматическая выдача не завершилась.\n\n"
            "Мы уже зафиксировали оплату и уведомили администратора. Напишите в поддержку, указав ID платежа: <code>{payment_id}</code>"
        ),
        "balance_topped_up": "<b>{balance_emoji} Баланс пополнен</b>\n\nСумма: {amount}\nТекущий баланс: {balance}",
        "payment_success_notified": (
            "<b>{order_emoji} Оплата подтверждена</b>\n\n"
            "{category_emoji} Товар: {product_title}\n"
            "{price_emoji} Стоимость: {amount}\n"
            "{category_emoji} Ключ:\n<code>{key_value}</code>\n\n"
            "Покупка сохранена в разделе «Мои покупки»."
        ),
        "secure_connection_error": "Не удалось установить защищенное соединение с платёжным шлюзом. Попробуйте еще раз через минуту.",
        "gateway_unavailable": "Платежный шлюз временно недоступен. Попробуйте еще раз чуть позже.",
        "invoice_create_failed": "Не удалось создать счет. Попробуйте еще раз позже.",
        "cryptopay_not_configured": "Crypto Pay не настроен",
        "lolz_not_configured": "Lolzteam не настроен",
        "payment_not_found": "Платёж не найден",
        "user_not_found": "Пользователь не найден",
        "product_unavailable": "Товар недоступен",
        "insufficient_balance": "Недостаточно средств на балансе",
        "unable_to_reserve_product": "Не удалось зарезервировать товар",
        "no_referral_balance": "Реферальный баланс пуст",
        "shop_product_fallback": "Товар магазина",
    },
    "en": {
        "choose_language_prompt": '{globus} Choose language / Выберите язык / Виберiть мову',
        "language_english": "English",
        "language_russian": "Russian",
        "language_ukrainian": "Ukrainian",
        "language_changed": "Interface language updated",
        "main_menu": (
            "<b>{greeting_emoji} Welcome, {full_name}!</b>\n\n"
            "{catalog_emoji} Here you can buy access to AI services both for personal use and for resale.\n\n"
            "{balance_emoji} Your balance: <b>{balance}</b>\n"
        ),
        "main_menu_catalog": "Product catalog",
        "main_menu_cabinet": "Profile",
        "main_menu_info": "Information",
        "info_menu_text": "<b><tg-emoji emoji-id=\"5357315181649076022\">ℹ️</tg-emoji> Information</b>\n\nChoose a section:",
        "info_user_agreement": "User agreement",
        "info_privacy_policy": "Privacy policy",
        "info_refund_policy": "Refund policy",
        "support": "Support",
        "to_main_menu": "Main menu",
        "cabinet_text": (
            "<b>{laptop_emoji} User profile</b>\n\n"
            "{cabinet_emoji} General information:\n"
            "├ Profile ID: <code>{profile_id}</code>\n"
            "├ Registration date: {created_at}\n"
            "└ Interface language: {language_name}\n\n"
            "{balance_emoji} Finance and balance:\n"
            "├ Current balance: {balance}\n"
            "├ Total deposited: {deposited}\n"
            "└ Total purchases: {spent}\n\n"
            "{orders_stats_emoji} Order statistics:\n"
            "└ Successfully completed: {orders_count} pcs."
        ),
        "cabinet_orders": "My purchases",
        "cabinet_deposit": "Top up",
        "cabinet_referral": "Referral program",
        "cabinet_language": "Change language",
        "language_menu_text": (
            "<b>{language_emoji} Interface language</b>\n\n"
            "Current language: {language_name}\n"
            "Choose an option:"
        ),
        "catalog_choose_category": "<b>{choose_emoji} Choose a category:</b>",
        "catalog_choose_product": "<b>{choose_emoji} Choose a product:</b>\n\n{catalog_emoji} Category: {category}",
        "category_not_found": "Category not found",
        "product_not_found": "Product not found",
        "order_not_found": "Order not found",
        "data_not_found": "Data not found",
        "product_out_of_stock": "Product is out of stock",
        "product_already_in_stock": "Product is already in stock",
        "stock_notifications_enabled": "Notifications enabled",
        "stock_notifications_disabled": "Notifications disabled",
        "product_card_text": (
            "<b>{category_emoji} {internal_name}</b>\n\n"
            "{catalog_emoji} Category: {category_title}\n"
            "{price_emoji} Price: {price}\n"
            "{stock_emoji} In stock: {stock_count} pcs.\n\n"
            "{description_emoji} Product description:\n{description}\n\n"
            "{important_emoji} Important information:\n{important_info}"
        ),
        "back_to_categories": "Back to categories",
        "place_order": "Place order",
        "back_to_list": "Back to list",
        "notify_on_restock": "Notify on restock",
        "stop_notify": "Disable notifications",
        "buy_menu_text": (
            "<b>{order_emoji} Payment method</b>\n\n"
            "{catalog_emoji} You are buying: {product_title}\n"
            "{amount_emoji} Amount due: {amount}\n\n"
            "Choose a convenient payment method:"
        ),
        "buy_balance_option": "Bot balance ({balance})",
        "cancel_purchase": "Cancel purchase",
        "order_success_text": (
            "<b>{order_emoji} Order #{order_id} completed successfully</b>\n\n"
            "{category_emoji} Product: {product_title}\n"
            "{price_emoji} Price: {amount}\n"
            "{key_emoji} Key: <code>{key_value}</code>\n\n"
            "The key is also saved in the “My purchases” section."
        ),
        "invoice_created_text": (
            "<b>{order_emoji} Payment invoice created</b>\n\n"
            "{category_emoji} Product: {product_title}\n"
            "{price_emoji} Amount: {amount}\n\n"
            "We have reserved the product for you until the invoice expires. After payment, the bot will automatically deliver the key."
        ),
        "orders_history_empty": "<b>{description_emoji} Purchase history</b>\n\nYou do not have any successful orders yet.",
        "orders_history_choose": "<b>{description_emoji} Purchase history</b>\n\nChoose an order:",
        "orders_list_item": "Order #{order_id} — {amount} ({date})",
        "orders_back_to_cabinet": "Back to profile",
        "orders_forward": "Next",
        "orders_back": "Back",
        "order_detail_text": (
            "<b>{order_emoji} Order #{order_id} — {created_at}</b>\n\n"
            "{category_emoji} Product: {product_title}\n"
            "{price_emoji} Price: {amount}\n"
            "{key_emoji} Key: <code>{key_value}</code>"
        ),
        "orders_to_list": "Back to orders",
        "deposit_unavailable": "Top-up is temporarily unavailable",
        "deposit_start_text": (
            "<b>{order_emoji} Balance top-up</b>\n\n"
            "Enter the amount in USD that you want to add to your internal wallet:"
        ),
        "cancel": "Cancel",
        "invalid_amount_input": "Enter a valid amount, for example: 25 or 25.50",
        "deposit_amount_text": (
            "<b>{order_emoji} Balance top-up</b>\n\n"
            "{amount_emoji} Amount: {amount}\n\n"
            "{choose_emoji} Choose a payment method:"
        ),
        "enter_amount_first": "Enter the top-up amount first",
        "payment_method_unavailable": "Payment method is unavailable",
        "deposit_invoice_created_text": (
            "<b>{order_emoji} Top-up invoice created</b>\n\n"
            "{amount_emoji} Amount: {amount}\n"
            "{stock_emoji} After successful payment, your balance will be credited automatically."
        ),
        "pay_invoice": "Pay invoice",
        "check_payment": "Check payment",
        "payment_confirmed": "Payment confirmed",
        "payment_confirmed_processing": "Payment confirmed, but delivery is still being processed",
        "invoice_expired": "Invoice expired",
        "invoice_expired_text": (
            "<b>{important_emoji} Invoice expired</b>\n\n"
            "{amount_emoji} Amount: {amount}\n\n"
            "If the payment did not go through in time, create a new invoice."
        ),
        "payment_pending_text": (
            "<b>{order_emoji} Payment has not been confirmed yet</b>\n\n"
            "Amount: {amount}\n"
            "If you have already paid the invoice, try checking the status again in a few seconds."
        ),
        "referral_text": (
            "<b>{referral_emoji} Referral program</b>\n\n"
            "Earn by inviting new users. You receive a percentage from their purchases and top-ups.\n\n"
            "{stats_emoji} Your statistics:\n"
            "├ Referred users: {referrals_count}\n"
            "├ Referral earnings: {earned}\n"
            "└ Available to withdraw: {available}\n\n"
            "{link_emoji} Your link:\n"
            "<code>{referral_link}</code>"
        ),
        "withdraw_to_balance": "Transfer to balance",
        "referral_balance_transferred": "Referral balance transferred to the main balance",
        "back": "Back",
        "restock_notification_text": "{stock_emoji} The product {product_title} is back in stock!",
        "restock_buy": "Buy",
        "restock_to_menu": "Menu",
        "crypto_deposit_description": "Telegram shop balance top-up",
        "crypto_product_description": "Product payment: {product_name}",
        "crypto_deposit_hidden_message": "After payment, return to the bot: the balance will be credited automatically.",
        "crypto_product_hidden_message": "After payment, the bot will automatically deliver the product and save the purchase in history.",
        "payment_fulfillment_issue": (
            "{important_emoji} Payment confirmed, but automatic delivery was not completed.\n\n"
            "We have already recorded the payment and notified the administrator. Contact support and specify the payment ID: <code>{payment_id}</code>"
        ),
        "balance_topped_up": "<b>{balance_emoji} Balance topped up</b>\n\nAmount: {amount}\nCurrent balance: {balance}",
        "payment_success_notified": (
            "<b>{order_emoji} Payment confirmed</b>\n\n"
            "{category_emoji} Product: {product_title}\n"
            "{price_emoji} Price: {amount}\n"
            "{category_emoji} Key:\n<code>{key_value}</code>\n\n"
            "The purchase has been saved in the “My purchases” section."
        ),
        "secure_connection_error": "Could not establish a secure connection to the payment gateway. Please try again in a minute.",
        "gateway_unavailable": "The payment gateway is temporarily unavailable. Please try again later.",
        "invoice_create_failed": "Could not create an invoice. Please try again later.",
        "cryptopay_not_configured": "Crypto Pay is not configured",
        "lolz_not_configured": "Lolzteam is not configured",
        "payment_not_found": "Payment not found",
        "user_not_found": "User not found",
        "product_unavailable": "Product is unavailable",
        "insufficient_balance": "Insufficient balance",
        "unable_to_reserve_product": "Could not reserve the product",
        "no_referral_balance": "Referral balance is empty",
        "shop_product_fallback": "Store product",
    },
    "uk": {
        "choose_language_prompt": '{globus} Choose language / Выберите язык / Виберiть мову',
        "language_english": "English",
        "language_russian": "Російська",
        "language_ukrainian": "Українська",
        "language_changed": "Мову інтерфейсу оновлено",
        "main_menu": (
            "<b>{greeting_emoji} Вітаємо, {full_name}!</b>\n\n"
            "{catalog_emoji} Тут ви можете придбати доступи до AI-сервісів як для себе, так і для перепродажу.\n\n"
            "{balance_emoji} Ваш баланс: <b>{balance}</b>\n"
        ),
        "main_menu_catalog": "Каталог товарів",
        "main_menu_cabinet": "Профіль",
        "main_menu_info": "Інформація",
        "info_menu_text": "<b><tg-emoji emoji-id=\"5357315181649076022\">ℹ️</tg-emoji> Інформація</b>\n\nОберіть потрібний розділ:",
        "info_user_agreement": "Користувацька угода",
        "info_privacy_policy": "Політика конфіденційності",
        "info_refund_policy": "Політика повернення",
        "support": "Підтримка",
        "to_main_menu": "У головне меню",
        "cabinet_text": (
            "<b>{laptop_emoji} Профіль користувача</b>\n\n"
            "{cabinet_emoji} Загальна інформація:\n"
            "├ ID профілю: <code>{profile_id}</code>\n"
            "├ Дата реєстрації: {created_at}\n"
            "└ Мова інтерфейсу: {language_name}\n\n"
            "{balance_emoji} Фінанси та баланс:\n"
            "├ Поточний баланс: {balance}\n"
            "├ Усього поповнено: {deposited}\n"
            "└ Сума покупок: {spent}\n\n"
            "{orders_stats_emoji} Статистика замовлень:\n"
            "└ Успішно виконано: {orders_count} шт."
        ),
        "cabinet_orders": "Мої покупки",
        "cabinet_deposit": "Поповнити",
        "cabinet_referral": "Реферальна програма",
        "cabinet_language": "Змінити мову",
        "language_menu_text": (
            "<b>{language_emoji} Мова інтерфейсу</b>\n\n"
            "Поточна мова: {language_name}\n"
            "Оберіть потрібний варіант:"
        ),
        "catalog_choose_category": "<b>{choose_emoji} Оберіть категорію:</b>",
        "catalog_choose_product": "<b>{choose_emoji} Оберіть товар:</b>\n\n{catalog_emoji} Категорія: {category}",
        "category_not_found": "Категорію не знайдено",
        "product_not_found": "Товар не знайдено",
        "order_not_found": "Замовлення не знайдено",
        "data_not_found": "Дані не знайдено",
        "product_out_of_stock": "Товар закінчився",
        "product_already_in_stock": "Товар уже в наявності",
        "stock_notifications_enabled": "Сповіщення увімкнено",
        "stock_notifications_disabled": "Сповіщення вимкнено",
        "product_card_text": (
            "<b>{category_emoji} {internal_name}</b>\n\n"
            "{catalog_emoji} Категорія: {category_title}\n"
            "{price_emoji} Вартість: {price}\n"
            "{stock_emoji} У наявності: {stock_count} шт.\n\n"
            "{description_emoji} Опис товару:\n{description}\n\n"
            "{important_emoji} Важлива інформація:\n{important_info}"
        ),
        "back_to_categories": "Назад до категорій",
        "place_order": "Оформити замовлення",
        "back_to_list": "Назад до списку",
        "notify_on_restock": "Сповістити про надходження",
        "stop_notify": "Не сповіщати",
        "buy_menu_text": (
            "<b>{order_emoji} Вибір способу оплати</b>\n\n"
            "{catalog_emoji} Ви купуєте: {product_title}\n"
            "{amount_emoji} Сума до оплати: {amount}\n\n"
            "Оберіть зручний спосіб оплати:"
        ),
        "buy_balance_option": "Баланс бота ({balance})",
        "cancel_purchase": "Скасувати покупку",
        "order_success_text": (
            "<b>{order_emoji} Замовлення #{order_id} успішно оформлено</b>\n\n"
            "{category_emoji} Товар: {product_title}\n"
            "{price_emoji} Вартість: {amount}\n"
            "{key_emoji} Ключ: <code>{key_value}</code>\n\n"
            "Ключ також збережено в розділі «Мої покупки»."
        ),
        "invoice_created_text": (
            "<b>{order_emoji} Рахунок на оплату створено</b>\n\n"
            "{category_emoji} Товар: {product_title}\n"
            "{price_emoji} Сума: {amount}\n\n"
            "Ми зарезервували для вас товар до завершення строку дії рахунку. Після оплати бот автоматично видасть ключ."
        ),
        "orders_history_empty": "<b>{description_emoji} Історія покупок</b>\n\nПоки що у вас немає успішних замовлень.",
        "orders_history_choose": "<b>{description_emoji} Історія покупок</b>\n\nОберіть потрібне замовлення:",
        "orders_list_item": "Замовлення #{order_id} — {amount} ({date})",
        "orders_back_to_cabinet": "До профілю",
        "orders_forward": "Далі",
        "orders_back": "Назад",
        "order_detail_text": (
            "<b>{order_emoji} Замовлення #{order_id} — {created_at}</b>\n\n"
            "{category_emoji} Товар: {product_title}\n"
            "{price_emoji} Вартість: {amount}\n"
            "{key_emoji} Ключ: <code>{key_value}</code>"
        ),
        "orders_to_list": "До списку замовлень",
        "deposit_unavailable": "Поповнення тимчасово недоступне",
        "deposit_start_text": (
            "<b>{order_emoji} Поповнення балансу</b>\n\n"
            "Введіть суму в USD, на яку ви хочете поповнити внутрішній гаманець:"
        ),
        "cancel": "Скасувати",
        "invalid_amount_input": "Введіть коректну суму, наприклад: 25 або 25.50",
        "deposit_amount_text": (
            "<b>{order_emoji} Поповнення балансу</b>\n\n"
            "{amount_emoji} Сума: {amount}\n\n"
            "{choose_emoji} Оберіть спосіб оплати:"
        ),
        "enter_amount_first": "Спочатку вкажіть суму поповнення",
        "payment_method_unavailable": "Спосіб оплати недоступний",
        "deposit_invoice_created_text": (
            "<b>{order_emoji} Рахунок на поповнення створено</b>\n\n"
            "{amount_emoji} Сума: {amount}\n"
            "{stock_emoji} Після успішної оплати баланс буде поповнено автоматично."
        ),
        "pay_invoice": "Сплатити рахунок",
        "check_payment": "Перевірити оплату",
        "payment_confirmed": "Платіж підтверджено",
        "payment_confirmed_processing": "Платіж підтверджено, але видача ще обробляється",
        "invoice_expired": "Строк дії рахунку минув",
        "invoice_expired_text": (
            "<b>{important_emoji} Строк дії рахунку минув</b>\n\n"
            "{amount_emoji} Сума: {amount}\n\n"
            "Якщо оплата не встигла пройти, створіть новий рахунок."
        ),
        "payment_pending_text": (
            "<b>{order_emoji} Платіж ще не підтверджено</b>\n\n"
            "Сума: {amount}\n"
            "Якщо ви вже оплатили рахунок, спробуйте перевірити статус ще раз за кілька секунд."
        ),
        "referral_text": (
            "<b>{referral_emoji} Реферальна програма</b>\n\n"
            "Заробляйте, запрошуючи нових користувачів. Ви отримуєте відсоток з їхніх покупок і поповнень.\n\n"
            "{stats_emoji} Ваша статистика:\n"
            "├ Запрошено рефералів: {referrals_count}\n"
            "├ Дохід з рефералів: {earned}\n"
            "└ Доступно до виведення: {available}\n\n"
            "{link_emoji} Ваше посилання:\n"
            "<code>{referral_link}</code>"
        ),
        "withdraw_to_balance": "Вивести на баланс",
        "referral_balance_transferred": "Реферальний баланс переведено на основний",
        "back": "Назад",
        "restock_notification_text": "{stock_emoji} Товар {product_title} знову в наявності!",
        "restock_buy": "Купити",
        "restock_to_menu": "У меню",
        "crypto_deposit_description": "Поповнення балансу Telegram-магазину",
        "crypto_product_description": "Оплата товару: {product_name}",
        "crypto_deposit_hidden_message": "Після оплати поверніться до бота: баланс буде поповнено автоматично.",
        "crypto_product_hidden_message": "Після оплати бот автоматично видасть товар і збереже покупку в історії.",
        "payment_fulfillment_issue": (
            "{important_emoji} Платіж підтверджено, але автоматична видача не завершилася.\n\n"
            "Ми вже зафіксували оплату та повідомили адміністратора. Напишіть у підтримку, вказавши ID платежу: <code>{payment_id}</code>"
        ),
        "balance_topped_up": "<b>{balance_emoji} Баланс поповнено</b>\n\nСума: {amount}\nПоточний баланс: {balance}",
        "payment_success_notified": (
            "<b>{order_emoji} Оплату підтверджено</b>\n\n"
            "{category_emoji} Товар: {product_title}\n"
            "{price_emoji} Вартість: {amount}\n"
            "{category_emoji} Ключ:\n<code>{key_value}</code>\n\n"
            "Покупку збережено в розділі «Мої покупки»."
        ),
        "secure_connection_error": "Не вдалося встановити захищене з'єднання з платіжним шлюзом. Спробуйте ще раз за хвилину.",
        "gateway_unavailable": "Платіжний шлюз тимчасово недоступний. Спробуйте ще раз трохи пізніше.",
        "invoice_create_failed": "Не вдалося створити рахунок. Спробуйте ще раз пізніше.",
        "cryptopay_not_configured": "Crypto Pay не налаштовано",
        "lolz_not_configured": "Lolzteam не налаштовано",
        "payment_not_found": "Платіж не знайдено",
        "user_not_found": "Користувача не знайдено",
        "product_unavailable": "Товар недоступний",
        "insufficient_balance": "Недостатньо коштів на балансі",
        "unable_to_reserve_product": "Не вдалося зарезервувати товар",
        "no_referral_balance": "Реферальний баланс порожній",
        "shop_product_fallback": "Товар магазину",
    },
}


ERROR_TRANSLATION_KEYS = {
    "Category not found": "category_not_found",
    "Категория не найдена": "category_not_found",
    "Product not found": "product_not_found",
    "Товар не найден": "product_not_found",
    "Order not found": "order_not_found",
    "Заказ не найден": "order_not_found",
    "Data not found": "data_not_found",
    "Данные не найдены": "data_not_found",
    "Product is out of stock": "product_out_of_stock",
    "Out of stock": "product_out_of_stock",
    "Товар закончился": "product_out_of_stock",
    "Product is already in stock": "product_already_in_stock",
    "Товар уже в наличии": "product_already_in_stock",
    "Payment not found": "payment_not_found",
    "Платёж не найден": "payment_not_found",
    "User not found": "user_not_found",
    "Пользователь не найден": "user_not_found",
    "Product is unavailable": "product_unavailable",
    "Товар недоступен": "product_unavailable",
    "Insufficient balance": "insufficient_balance",
    "Не удалось зарезервировать товар": "unable_to_reserve_product",
    "No referral balance available": "no_referral_balance",
    "Crypto Pay не настроен": "cryptopay_not_configured",
    "Lolzteam не настроен": "lolz_not_configured",
}


def normalize_language_code(raw_value: str | None) -> str:
    if not raw_value:
        return "ru"
    normalized = raw_value.strip().lower().replace("_", "-")
    if normalized.startswith("en"):
        return "en"
    if normalized.startswith("uk") or normalized.startswith("ua"):
        return "uk"
    if normalized.startswith("ru"):
        return "ru"
    return "ru"


def tr(language_code: str | None, key: str, **kwargs: Any) -> str:
    lang = normalize_language_code(language_code)
    template = TRANSLATIONS.get(lang, TRANSLATIONS["ru"]).get(key) or TRANSLATIONS["ru"][key]
    return template.format(**kwargs)


def language_name(language_code: str | None, ui_language_code: str | None = None) -> str:
    lang = normalize_language_code(language_code)
    target_ui_lang = normalize_language_code(ui_language_code or lang)
    mapping = {
        "en": "language_english",
        "ru": "language_russian",
        "uk": "language_ukrainian",
    }
    return tr(target_ui_lang, mapping[lang])


def pick_localized_text(localized_values: dict[str, str] | None, language_code: str | None, fallback: str = "") -> str:
    values = localized_values or {}
    lang = normalize_language_code(language_code)
    for candidate in (lang, "ru", "en", "uk"):
        value = str(values.get(candidate, "")).strip()
        if value:
            return value
    return str(fallback or "").strip()


def translate_error(language_code: str | None, raw_message: str) -> str:
    key = ERROR_TRANSLATION_KEYS.get(raw_message.strip())
    if key:
        return tr(language_code, key)
    return raw_message
