# bot.py — повний робочий код з виправленнями

import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --------------------------
TOKEN = "8321988283:AAHaMPgWW68Ktmek1WAdTeZjeLMJquT0IUk"
SPREADSHEET_ID = "1lJc616p6Mx0QBAXexmBJxYX9cte8cSBANJQNaR2V12w"
SERVICE_ACCOUNT_FILE = "teak-alloy-475620-q5-75d9468a5b71.json"
ADMIN_CHAT_ID = 460841825  # <- твій chat_id

# --------------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
gc = gspread.authorize(credentials)
SPREADSHEET = gc.open_by_key(SPREADSHEET_ID)

# Аркуші
SHEET_PRAYER = SPREADSHEET.sheet1
try:
    SHEET_OTHERS = SPREADSHEET.get_worksheet(1)
except Exception:
    SHEET_OTHERS = SPREADSHEET.add_worksheet(title="Молитва за інших", rows="100", cols="10")
    SHEET_OTHERS.append_row(["Дата", "Ім'я", "Молитва", "Періодичність", "Телефон"])
try:
    SHEET_KVL = SPREADSHEET.get_worksheet(2)
except Exception:
    SHEET_KVL = SPREADSHEET.add_worksheet(title="КВЛ", rows="100", cols="5")
    SHEET_KVL.append_row(["Дата і час", "Ім'я та Прізвище", "Місто", "Область", "Телефон"])

# --------------------------
def main_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🙏 Залишити намірення", callback_data="pray_request")],
            [InlineKeyboardButton("✝️ Приєднатись до молитви", callback_data="pray_for_others")],
            [InlineKeyboardButton("🛡️ Більше про Круціяту Визволення Людини", callback_data="crusade")],
        ]
    )


# --------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Слава Ісусу Христу!\n\n"
        "Це сторінка молитовної ініціативи Круціяти Визволення Людини\n 🔥Смолоскипи Гедеона🔥\n\n"
        "Тут Ви можете:\n"
        "🙏 Залишити намірення за ЗВІЛЬНЕННЯ ЛЮДИНИ ІЗ ЗАЛЕЖНОСТІ\n"
        "✝️ Приєднатись до молитви за залежних осіб\n"
        "🛡️ Дізнатись більше про Круціяту Визволення Людини\n\n"
        "Тож, розпочнімо!",
        reply_markup=main_keyboard(),
    )


# --------------------------
# Обробник кліків для кнопок періодичності
async def periodicity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data  # 'daily' / 'weekly' / 'monthly'

    mapping = {"daily": "Щодня", "weekly": "Щотижня", "monthly": "Щомісяця"}
    context.user_data["periodicity"] = mapping.get(data, data)
    # наступний крок — введення телефону
    context.user_data["step_others"] = 4

    await query.message.reply_text(
        "Дякуємо! 🙏\nЯкщо бажаєте, залиште свій номер телефону для зв’язку (або напишіть «–», щоб пропустити):"
    )


# --------------------------
# Загальний обробник меню / callback-ів
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Не чистимо user_data тут — стан зберігається під час покрокової взаємодії.
    # Чистимо тільки коли користувач повертається в головне меню або після завершення сценарію.

    if data == "pray_request":
        context.user_data.clear()
        context.user_data["step"] = 1
        await query.message.reply_text(
            "Введіть ім'я (за бажанням прізвище) людини, за яку Ви просите помолитись у намірі: ЗА ЗВІЛЬНЕННЯ ІЗ ЗАЛЕЖНОСТІ",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 На початок", callback_data="back_to_start")]]),
        )
        return

    if data == "pray_for_others":
        context.user_data.clear()
        context.user_data["step_others"] = 1
        await query.message.reply_text(
            "Введіть, будь ласка, своє ім'я та прізвище 🙏\n(Ви можете написати тільки ім’я, якщо бажаєте)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 На початок", callback_data="back_to_start")]]),
        )
        return

    if data == "crusade":
        # інформація + кнопка приєднатись
        await query.message.reply_text(
            "🛡️Що таке Круціята Визволення Людини?\n\n"
"КВЛ - це програма дій, метою якої є подолання всього, що загрожує гідності особи та принижує здорові суспільні звичаї. \n"
"Тому КВЛ пропагує стиль життя, що спирається на правду, любов і свободу. До участі в Круціяті ми запрошуємо кожну людину доброї волі.\n"
"Круціята Визволення Людини - це служіння заради визволення від залежностей, поширених в суспільстві, алкоголізму, та усякої омани і страху, особливо які нищать людську гідність і не дозволяють людині самореалізуватися згідно зі своїм покликанням.\n\n"
            "Додатково:\n"
            "🔹 Facebook: https://www.facebook.com/groups/253007735269596/\n"
            "🔹 Сайт Руху Світло-Життя: https://oazaukraina.blogspot.com/2010/10/blog-post_5048.html\n"
            "🔹 Вікіпедія: https://uk.wikipedia.org/wiki/Круціята_визволення_людини\n\n"
            "Якщо бажаєте приєднатись до КВЛ, натисніть кнопку нижче 👇",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Виявляю бажання приєднатись до КВЛ", callback_data="join_kvl")],
                    [InlineKeyboardButton("🔙 На початок", callback_data="back_to_start")],
                ]
            ),
        )
        return

    if data == "back_to_start":
        context.user_data.clear()
        await query.message.reply_text("Головне меню:", reply_markup=main_keyboard())
        return

    if data == "join_kvl":
        context.user_data.clear()
        context.user_data["kvl_step"] = 1
        await query.message.reply_text(
            "Введіть, будь ласка, ім’я та прізвище 🙏",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 На початок", callback_data="back_to_start")]]),
        )
        return

    # Якщо callback не впізнано — ігноруємо (або лог)
    logger.info(f"Unprocessed callback data: {data}")


# --------------------------
# Обробляємо текстові повідомлення (всі кроки)
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- Прошу про молитву ---
    if context.user_data.get("step") == 1:
        SHEET_PRAYER.append_row([timestamp, text])
        await update.message.reply_text(
            "Дякуємо! Ваше прохання отримано. Нехай Бог Вам благословить 🙏",
            reply_markup=main_keyboard(),
        )
        context.user_data.clear()
        return

    # --- Хочу молитись за інших ---
    step_others = context.user_data.get("step_others")
    if step_others:
        if step_others == 1:
            context.user_data["name"] = text
            context.user_data["step_others"] = 2
            await update.message.reply_text(
                "Дякуємо 👍\nНапишіть, будь ласка, яку молитву Ви бажаєте молитися за інших "
                "(наприклад: «Отче наш», «Розарій», «Коронка до Божого Милосердя» тощо)."
            )
            return

        if step_others == 2:
            context.user_data["prayer"] = text
            context.user_data["step_others"] = 3
            # відправляємо кнопки періодичності
            await update.message.reply_text(
                "Гарно! 🙌\nЯк часто Ви плануєте молитися?\nОберіть, будь ласка, варіант нижче 👇",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("🔹 Щодня", callback_data="daily")],
                        [InlineKeyboardButton("🔹 Щотижня", callback_data="weekly")],
                        [InlineKeyboardButton("🔹 Щомісяця", callback_data="monthly")],
                    ]
                ),
            )
            return

        if step_others == 4:
            phone = text if text else "-"
            # Запис у Google Sheets
            SHEET_OTHERS.append_row(
                [
                    timestamp,
                    context.user_data.get("name", "-"),
                    context.user_data.get("prayer", "-"),
                    context.user_data.get("periodicity", "-"),
                    phone,
                ]
            )
            await update.message.reply_text(
                "✅ Дякуємо, що зголосились молитись за інших!\nНехай Господь щедро благословить Вас 🕊️",
                reply_markup=main_keyboard(),
            )
            context.user_data.clear()
            return

    # --- КВЛ ---
    kvl_step = context.user_data.get("kvl_step")
    if kvl_step:
        if kvl_step == 1:
            context.user_data["name"] = text
            context.user_data["kvl_step"] = 2
            await update.message.reply_text("Введіть, будь ласка, місто:")
            return
        if kvl_step == 2:
            context.user_data["city"] = text
            context.user_data["kvl_step"] = 3
            await update.message.reply_text("Введіть, будь ласка, область:")
            return
        if kvl_step == 3:
            context.user_data["region"] = text
            context.user_data["kvl_step"] = 4
            await update.message.reply_text("Введіть, будь ласка, номер телефону (або «–», щоб пропустити):")
            return
        if kvl_step == 4:
            phone = text if text else "-"
            # Запис у Google Sheets
            SHEET_KVL.append_row(
                [timestamp, context.user_data.get("name", "-"), context.user_data.get("city", "-"),
                 context.user_data.get("region", "-"), phone]
            )

            # Сповіщення адміністратору (без падіння при помилці)
            if ADMIN_CHAT_ID:
                try:
                    await context.bot.send_message(
                        chat_id=ADMIN_CHAT_ID,
                        text=(
                            "⚠️ Новий учасник КВЛ:\n"
                            f"Ім’я: {context.user_data.get('name')}\n"
                            f"Місто: {context.user_data.get('city')}\n"
                            f"Область: {context.user_data.get('region')}\n"
                            f"Телефон: {phone}"
                        ),
                    )
                except Exception as e:
                    logger.error(f"Не вдалося надіслати сповіщення адміністратору: {e}")

            # Підтвердження користувачу
            await update.message.reply_text(
                "✅ Дякуємо за бажання приєднатись до КВЛ!\nНехай Господь щедро благословить Вас 🕊️\n\n"
                "Контакти відповідальних осіб:\n"
"🔹 о. Павло Росса +380972657312\n"
"🔹 Барбара +380974656801\n"
"🔹 Дмитро +380634287204\n\n"
                "Посилання на сторінки КВЛ:\n\n"
            "🔹 Facebook: https://www.facebook.com/groups/253007735269596/\n"
            "🔹 Сайт Руху Світло-Життя: https://oazaukraina.blogspot.com/2010/10/blog-post_5048.html\n"
            "🔹 Вікіпедія: https://uk.wikipedia.org/wiki/Круціята_визволення_людини\n\n"
            )

            context.user_data.clear()
            return

    # Якщо повідомлення не відноситься до жодного кроку, просто показуємо головне меню
    await update.message.reply_text("Оберіть дію:", reply_markup=main_keyboard())


# --------------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Додаємо handler-и: спочатку періодичність (щоб pattern спрацьовував раніше),
    # потім загальний menu_handler, потім інші.
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(periodicity_handler, pattern="^(daily|weekly|monthly)$"))
    app.add_handler(CallbackQueryHandler(menu_handler))  # обробляє інші callback_data
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Бот запущено. Ctrl+C для зупинки.")
    app.run_polling()


if __name__ == "__main__":
    main()
