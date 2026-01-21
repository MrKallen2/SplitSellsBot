import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram.error import BadRequest

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "8538557437:AAGhzBNEgpsFJKrOEzJg5NAwTFIJWBb1IAM"
ADMIN_ID = 7626450915  # Ваш ID в Telegram (можно узнать у @userinfobot)

# Данные для оплаты
PAYMENT_DETAILS = {
    "card_number": "2204310361076766",
}

# Цены аккаунтов (рублей)
ACCOUNTS = {
    "split_20000": {
        "name": "Аккаунт с лимитом 20,000 ₽",
        "price": 1399,
        "description": "Аккаунт Яндекс.Сплит с лимитом: 20,000 рублей\nТип получения: Логин и пароль"
    },
    "split_30000": {
        "name": "Аккаунт с лимитом 30,000 ₽",
        "price": 1999,
        "description": "Аккаунт Яндекс с лимитом: 30,000 рублей\nТип получения: Логин и пароль"
    },
    "split_50000": {
        "name": "Аккаунт с лимитом 50,000 ₽",
        "price": 2599,
        "description": "Аккаунт Яндекс с лимитом: 50,000 рублей\nТип получения: Логин и пароль"
    },
    "split_70000": {
        "name": "Аккаунт с лимитом 70,000 ₽",
        "price": 3199,
        "description": "Аккаунт Яндекс с лимитом: 70,000 рублей\nТип получения: Логин и пароль"
    },
    "split_100000": {
        "name": "Аккаунт с лимитом 100,000 ₽",
        "price": 4599,
        "description": "Аккаунт Яндекс с лимитом: 100,000 рублей\nТип получения: Логин и пароль"
    },
    "split_150000": {
        "name": "Аккаунт с лимитом 150,000 ₽",
        "price": 5399,
        "description": "Аккаунт Яндекс с лимитом: 150,000 рублей\nТип получения: Логин и пароль"
    },
    "split_200000": {
        "name": "Аккаунт с лимитом 200,000 ₽",
        "price": 6199,
        "description": "Аккаунт Яндекс с лимитом: 200,000 рублей\nТип получения: Логин и пароль"
    }
}

# Состояния для ConversationHandler
(
    MAIN_MENU,
    SELECTING_ACCOUNT,
    CONFIRMING_ORDER,
    PAYMENT_INFO,
    WAITING_RECEIPT,
    PROCESSING_PAYMENT
) = range(6)

# Хранилище заказов (в реальном боте лучше использовать базу данных)
orders = {}


# --- Клавиатуры ---
def get_main_keyboard():
    """Главное меню - Inline клавиатура"""
    keyboard = [
        [InlineKeyboardButton("🛒 Каталог аккаунтов", callback_data='catalog')],
        [InlineKeyboardButton("📞 Связь с поддержкой", callback_data='support')],
        [InlineKeyboardButton("❓ FAQ / Помощь", callback_data='faq')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_reply_keyboard():
    """Reply клавиатура с кнопкой Главное меню"""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🏠 Главное меню")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_catalog_keyboard():
    """Каталог аккаунтов"""
    keyboard = []
    for key, account in ACCOUNTS.items():
        button_text = f"{account['name']} - {account['price']:,} ₽"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f'select_{key}')])

    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    return InlineKeyboardMarkup(keyboard)


def get_confirm_keyboard(account_key):
    """Клавиатура подтверждения заказа"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить заказ", callback_data=f'confirm_{account_key}'),
            InlineKeyboardButton("❌ Отменить", callback_data='cancel')
        ],
        [InlineKeyboardButton("◀️ Назад к каталогу", callback_data='back_to_catalog')]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_payment_methods_keyboard():
    """Клавиатура выбора способа оплаты"""
    keyboard = [
        [InlineKeyboardButton("💳 Оплата картой", callback_data='payment_card')],
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_catalog')]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_after_payment_keyboard(order_id):
    """Клавиатура после показа реквизитов"""
    keyboard = [
        [InlineKeyboardButton("📸 Отправить чек об оплате", callback_data=f'send_receipt_{order_id}')],
        [InlineKeyboardButton("❌ Отменить заказ", callback_data=f'cancel_order_{order_id}')],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_main_keyboard():
    """Просто кнопка назад в главное меню"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]])


# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_text = f"""
👋 Привет, {user.first_name}!

Добро пожаловать в **SplitSells** — бот для покупки проверенных аккаунтов с готовым лимитом Сплита для ваших покупок!

🎯 **Что у нас есть:**
• Аккаунты с лимитом от 20,000 до 200,000 рублей
• Моментальная выдача после оплаты
• Полная гарантия и поддержка 24/7

Выбери действие:
"""
    if update.message:
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        # Показываем Reply клавиатуру без лишнего текста
        await update.message.reply_text(
            "Используйте кнопки меню выше или нажмите кнопку ниже:",
            reply_markup=get_main_reply_keyboard()
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            welcome_text,
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
    return MAIN_MENU

async def handle_main_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Главное меню' в Reply клавиатуре"""
    user = update.effective_user
    welcome_text = f"""
🏠 **Главное меню**

👋 Привет, {user.first_name}!

Выбери действие:
"""
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )
    return MAIN_MENU


async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать каталог"""
    query = update.callback_query
    await query.answer()

    catalog_text = """
💰 **Каталог аккаунтов**

Выберите аккаунт с нужным лимитом Яндекс.Сплит:

*Цены указаны за логин и пароль к аккаунту*
"""
    await query.edit_message_text(
        catalog_text,
        reply_markup=get_catalog_keyboard(),
        parse_mode='Markdown'
    )
    return SELECTING_ACCOUNT


async def select_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор конкретного аккаунта"""
    query = update.callback_query
    await query.answer()

    account_key = query.data.replace('select_', '')
    account = ACCOUNTS[account_key]

    context.user_data['selected_account'] = account_key

    order_text = f"""
📋 **Детали заказа**

🏷️ **Название:** {account['name']}
💰 **Стоимость:** {account['price']:,} ₽
📝 **Описание:** {account['description']}

📦 **Что вы получаете:**
• Логин и пароль от аккаунта Яндекс
• Лимит Яндекс.Сплит: {account['price']:,} ₽
• Инструкция по использованию

⚡ **Процесс покупки:**
1. Подтверждаете заказ
2. Получаете реквизиты для оплаты
3. Оплачиваете
4. Отправляете чек
5. Получаете данные аккаунта

Подтвердить заказ?
"""
    await query.edit_message_text(
        order_text,
        reply_markup=get_confirm_keyboard(account_key),
        parse_mode='Markdown'
    )
    return CONFIRMING_ORDER


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение заказа и переход к оплате"""
    query = update.callback_query
    await query.answer()

    account_key = query.data.replace('confirm_', '')
    account = ACCOUNTS[account_key]
    user = query.from_user

    # Генерируем ID заказа
    order_id = f"ORDER_{user.id}_{int(datetime.now().timestamp())}"

    # Сохраняем информацию о заказе
    order_info = {
        'order_id': order_id,
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'account': account['name'],
        'account_key': account_key,
        'price': account['price'],
        'status': 'pending_payment',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'receipt_sent': False
    }

    # Сохраняем заказ
    orders[order_id] = order_info
    context.user_data['current_order_id'] = order_id

    # Показываем способы оплаты
    payment_methods_text = f"""
✅ **Заказ подтвержден!**

🏷️ **Название:** {account['name']}
💰 **К оплате:** {account['price']:,} ₽
🆔 **Номер заказа:** `{order_id}`

👇 **Выберите способ оплаты:**
"""
    await query.edit_message_text(
        payment_methods_text,
        reply_markup=get_payment_methods_keyboard(),
        parse_mode='Markdown'
    )
    return PAYMENT_INFO


async def show_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать реквизиты для оплаты картой"""
    query = update.callback_query
    await query.answer()

    order_id = context.user_data.get('current_order_id')
    if not order_id or order_id not in orders:
        await query.edit_message_text(
            "❌ Ошибка: заказ не найден. Начните заново.",
            reply_markup=get_back_to_main_keyboard()
        )
        return MAIN_MENU

    order = orders[order_id]
    account = ACCOUNTS[order['account_key']]

    payment_text = f"""
💳 **ОПЛАТА КАРТОЙ**

🏷️ **Заказ:** {order['account']}
💰 **Сумма к оплате:** {order['price']:,} ₽
🆔 **Номер заказа:** `{order_id}`

📋 **Реквизиты для перевода:**

🔢 **Номер карты:** `{PAYMENT_DETAILS['card_number']}`

⚠️ **ВАЖНО:**
1. Сохраните скриншот чека об оплате
2. После оплаты нажмите кнопку "📸 Отправить чек об оплате"

⏳ **После отправки чека:**
• В течение 10-60 минут менеджер проверит оплату
• После проверки вы получите данные аккаунта
"""
    await query.edit_message_text(
        payment_text,
        reply_markup=get_after_payment_keyboard(order_id),
        parse_mode='Markdown'
    )
    return WAITING_RECEIPT


async def request_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос отправки чека"""
    query = update.callback_query
    await query.answer()

    order_id = query.data.replace('send_receipt_', '')
    context.user_data['current_order_id'] = order_id

    receipt_text = """
📸 **Отправьте чек об оплате**

Пожалуйста, отправьте скриншот или фото чека об оплате.

**Требования к чеку:**
• Должна быть видна сумма перевода
• Должен быть виден номер заказа или комментарий
• Изображение должно быть четким

📤 **Просто отправьте фото/скриншот в этот чат**

❓ **Если возникли проблемы:**
• Попробуйте сжать изображение
• Или свяжитесь с поддержкой
"""
    await query.edit_message_text(
        receipt_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отменить", callback_data=f'cancel_order_{order_id}')],
            [InlineKeyboardButton("📞 Поддержка", url="https://t.me/d0ggy227")]
        ])
    )
    return WAITING_RECEIPT


async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка полученного чека"""
    order_id = context.user_data.get('current_order_id')

    if not order_id or order_id not in orders:
        await update.message.reply_text(
            "❌ Ошибка: заказ не найден. Начните заново с /start",
            reply_markup=get_main_reply_keyboard()
        )
        return MAIN_MENU

    order = orders[order_id]

    if update.message.photo:
        # Получаем самое большое фото
        photo = update.message.photo[-1]

        # Обновляем статус заказа
        order['status'] = 'payment_verification'
        order['receipt_sent'] = True
        order['receipt_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Уведомляем администратора
        admin_message = f"""
📸 **ПОЛУЧЕН ЧЕК ОБ ОПЛАТЕ!**

🆔 **Номер заказа:** {order_id}
👤 **Покупатель:** {order['first_name']} (@{order['username'] if order['username'] else 'нет'})
💰 **Сумма:** {order['price']:,} ₽
🏷️ **Аккаунт:** {order['account']}
⏰ **Время отправки чека:** {order['receipt_time']}

⚠️ **Требуется проверка оплаты!**
"""
        try:
            # Отправляем сообщение админу
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode='Markdown'
            )

            # Пересылаем чек админу
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo.file_id,
                caption=f"Чек по заказу: {order_id}"
            )

        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу: {e}")

        # Сообщение пользователю
        user_message = f"""
✅ **Чек получен!**

Спасибо! Ваш чек по заказу `{order_id}` успешно получен.

⏳ **Статус:** Ожидает проверки оплаты

📋 **Что дальше:**
1. Наш менеджер проверяет поступление средств (10-60 минут)
2. После подтверждения оплаты вы получите данные аккаунта
3. Если будут вопросы — с вами свяжутся

🕐 **Среднее время проверки:** 10-60 минут

💬 **По всем вопросам:** @d0ggy227

⚠️ **Не удаляйте этот чат!** Здесь вы получите данные аккаунта.
"""
        await update.message.reply_text(
            user_message,
            reply_markup=get_main_reply_keyboard(),
            parse_mode='Markdown'
        )

        return MAIN_MENU

    else:
        await update.message.reply_text(
            "❌ Пожалуйста, отправьте именно фото или скриншот чека.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📸 Отправить чек", callback_data=f'send_receipt_{order_id}')],
                [InlineKeyboardButton("❌ Отменить", callback_data=f'cancel_order_{order_id}')]
            ])
        )
        return WAITING_RECEIPT


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена заказа"""
    query = update.callback_query
    await query.answer()

    if 'cancel_order_' in query.data:
        order_id = query.data.replace('cancel_order_', '')
        if order_id in orders:
            orders.pop(order_id)

    cancel_text = """
❌ **Заказ отменен**

Ваш заказ был успешно отменен.

🛒 Вы можете выбрать другой аккаунт или вернуться в главное меню.
"""
    await query.edit_message_text(
        cancel_text,
        reply_markup=get_back_to_main_keyboard()
    )

    if 'current_order_id' in context.user_data:
        context.user_data.pop('current_order_id')

    return MAIN_MENU


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Связь с поддержкой"""
    query = update.callback_query
    await query.answer()

    support_text = """
📞 **Связь с поддержкой**

По вопросам покупки, оплаты или техническим проблемам:

👨‍💻 **Менеджер:** @d0ggy227
⏰ **Рабочее время:** 24/7

*Ответ в течение 5-15 минут*
"""
    await query.edit_message_text(
        support_text,
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )
    return MAIN_MENU


async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FAQ"""
    query = update.callback_query
    await query.answer()

    faq_text = """
❓ **Частые вопросы**

🤔 **Что такое Яндекс.Сплит?**
- Это сервис для оплаты покупок частями, аналог рассрочки.

🔒 **Аккаунты легальные?**
- Да, все аккаунты созданы официально, прогреты и готовы к использованию.

⏱️ **Как быстро получу доступ?**
- В течение 10-60 минут после отправки чека об оплате.

💳 **Какие способы оплаты?**
- Банковская карта (РФ/зарубежная)

🔄 **Есть ли гарантия?**
- Да, гарантируем вход в аккаунт. При проблемах — замена или возврат средств.

📸 **Что делать, если не получается отправить чек?**
- Свяжитесь с поддержкой
"""
    await query.edit_message_text(
        faq_text,
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )
    return MAIN_MENU


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    query = update.callback_query
    await query.answer()

    await start(update, context)


async def back_to_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в каталог"""
    query = update.callback_query
    await query.answer()

    await catalog(update, context)


async def cancel_simple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Простая отмена (без order_id)"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "❌ Действие отменено.\n\nВозвращаемся в главное меню...",
        reply_markup=get_main_keyboard()
    )
    return MAIN_MENU


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик неизвестных команд"""
    await update.message.reply_text(
        "Извините, я не понимаю эту команду. Используйте кнопки меню.",
        reply_markup=get_main_keyboard()
    )
    return MAIN_MENU


# --- Основная функция ---
def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Настройка ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(catalog, pattern='^catalog$'),
            CallbackQueryHandler(support, pattern='^support$'),
            CallbackQueryHandler(faq, pattern='^faq$'),
            CallbackQueryHandler(back_to_main, pattern='^back_to_main$'),
            MessageHandler(filters.TEXT & ~filters.COMMAND, start),  # Обработка кнопки Start
            MessageHandler(filters.Regex("^(🏠 Главное меню)$"), handle_main_menu_button),  # Обработка кнопки Reply
        ],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(catalog, pattern='^catalog$'),
                CallbackQueryHandler(support, pattern='^support$'),
                CallbackQueryHandler(faq, pattern='^faq$'),
                MessageHandler(filters.Regex("^(🏠 Главное меню)$"), handle_main_menu_button),
            ],
            SELECTING_ACCOUNT: [
                CallbackQueryHandler(select_account, pattern='^select_'),
                CallbackQueryHandler(back_to_main, pattern='^back_to_main$'),
                CallbackQueryHandler(back_to_catalog, pattern='^back_to_catalog$'),
                MessageHandler(filters.Regex("^(🏠 Главное меню)$"), handle_main_menu_button),
            ],
            CONFIRMING_ORDER: [
                CallbackQueryHandler(confirm_order, pattern='^confirm_'),
                CallbackQueryHandler(cancel_simple, pattern='^cancel$'),
                CallbackQueryHandler(back_to_catalog, pattern='^back_to_catalog$'),
                MessageHandler(filters.Regex("^(🏠 Главное меню)$"), handle_main_menu_button),
            ],
            PAYMENT_INFO: [
                CallbackQueryHandler(show_payment_details, pattern='^payment_card$'),
                CallbackQueryHandler(back_to_catalog, pattern='^back_to_catalog$'),
                CallbackQueryHandler(cancel_simple, pattern='^cancel$'),
                MessageHandler(filters.Regex("^(🏠 Главное меню)$"), handle_main_menu_button),
            ],
            WAITING_RECEIPT: [
                CallbackQueryHandler(request_receipt, pattern='^send_receipt_'),
                CallbackQueryHandler(cancel_order, pattern='^cancel_order_'),
                MessageHandler(filters.PHOTO, handle_receipt),
                MessageHandler(filters.Regex("^(🏠 Главное меню)$"), handle_main_menu_button),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CallbackQueryHandler(back_to_main, pattern='^back_to_main$'),
            CallbackQueryHandler(cancel_simple, pattern='^cancel$'),
            MessageHandler(filters.Regex("^(🏠 Главное меню)$"), handle_main_menu_button),
        ],
        per_message=False,
        allow_reentry=True
    )

    # Регистрируем ConversationHandler
    application.add_handler(conv_handler)

    # Обработчик неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND, unknown))

    # Запускаем бота
    print("🤖 Бот запущен с Reply клавиатурой 'Главное меню'...")
    print(f"💳 Реквизиты для оплаты: {PAYMENT_DETAILS['card_number']}")
    print(f"👤 Админ: {ADMIN_ID}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()