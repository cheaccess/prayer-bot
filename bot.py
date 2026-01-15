# bot.py — повний робочий код з Flask + Webhook для Render
import logging
import os
import json
from datetime import datetime
from flask import Flask, request

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
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
TOKEN = os.getenv("BOT_TOKEN") or "PUT_TOKEN_HERE"
SPREADSHEET_ID = "1lJc616p6Mx0QBAXexmBJxYX9cte8cSBANJQNaR2V12w"
ADMIN_CHAT_ID = 460841825

WEBHOOK_PATH = f"/webhook/{TOKEN}"

# --------------------------
# Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
credentials_info = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_info, scope)

gc = gspread.authorize(credentials)
SPREADSHEET = gc.open_by_key(SPREADSHEET_ID)

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
async def periodicity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mapping = {"daily": "Щодня", "weekly": "Щотижня", "monthly": "Щомісяця"}
    context.user_data["periodicity"] = mapping.get(query.data)
    context.user_data["step_others"] = 4
    await query.message.reply_text(
        "Дякуємо! 🙏\nЯкщо бажаєте, залиште свій номер телефону для зв’язку (або напишіть «–», щоб пропустити):"
    )

# --------------------------
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

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
        await query.message.reply_text(
            "🛡️Що таке Круціята Визволення Людини?\n\n"
            "КВЛ - це програма дій, метою якої є подолання всього, що загрожує гідності особи...\n\n"
            "Додатково:\n"
            "🔹 Facebook: https://www.facebook.com/groups/253007735269596/\n"
            "🔹 Сайт Руху Світло-Життя: https://oazaukraina.blogspot.com/2010/10/blog-post_5048.html\n"
            "🔹 Вікіпедія: https://uk.wikipedia.org/wiki/Круціята_визволення_людини\n\n",
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

# --------------------------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if context.user_data.get("step") == 1:
        SHEET_PRAYER.append_row([timestamp, text])
        await update.message.reply_text("Дякуємо! 🙏", reply_markup=main_keyboard())
        context.user_data.clear()
        return

# --------------------------
def create_app():
    flask_app = Flask(__name__)
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(periodicity_handler, pattern="^(daily|weekly|monthly)$"))
    application.add_handler(CallbackQueryHandler(menu_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    @flask_app.route("/")
    def home():
        return "Bot is running ✅"

    @flask_app.route(WEBHOOK_PATH, methods=["POST"])
    async def webhook():
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return "OK"

    return flask_app, application

# --------------------------
if __name__ == "__main__":
    flask_app, application = create_app()

    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path=WEBHOOK_PATH,
        webhook_url=os.getenv("RENDER_EXTERNAL_URL") + WEBHOOK_PATH,
    )
