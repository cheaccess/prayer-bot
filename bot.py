# bot.py — повний робочий код з WEBHOOK для Render + Google Sheets
import os
import json
import logging
from datetime import datetime
from flask import Flask, request

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
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
# Logging
# --------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --------------------------
# Telegram / Google Sheets config
# --------------------------
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = TOKEN
WEBHOOK_PATH = "/webhook"

SPREADSHEET_ID = "1lJc616p6Mx0QBAXexmBJxYX9cte8cSBANJQNaR2V12w"

# Google Sheets auth
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

# --------------------------
# Flask app
# --------------------------
flask_app = Flask(__name__)

# --------------------------
# Keyboards
# --------------------------
def main_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🙏 Залишити намірення", callback_data="pray_request")],
            [InlineKeyboardButton("✝️ Приєднатись до молитви", callback_data="pray_for_others")],
            [InlineKeyboardButton("🛡️ Більше про Круціяту Визволення Людини", callback_data="crusade")],
        ]
    )

def periodicity_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Щодня", callback_data="daily"),
                InlineKeyboardButton("Щотижня", callback_data="weekly"),
                InlineKeyboardButton("Щомісяця", callback_data="monthly"),
            ]
        ]
    )

# --------------------------
# Telegram Handlers
# --------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Слава Ісусу Христу!\n\n"
        "Ласкаво просимо до молитовної ініціативи 🔥Смолоскипи Гедеона🔥\n\n"
        "Оберіть опцію нижче:",
        reply_markup=main_keyboard(),
    )

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "pray_request":
        context.user_data["periodicity"] = None
        await query.edit_message_text(
            "Оберіть періодичність молитовного наміру:",
            reply_markup=periodicity_keyboard(),
        )
    elif data == "pray_for_others":
        await query.edit_message_text("Ви приєдналися до молитви за інших 🙏")
    elif data == "crusade":
        await query.edit_message_text(
            "Круціята Визволення Людини — це молитовна ініціатива, ... (тут можна вставити текст)."
        )

async def periodicity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    context.user_data["periodicity"] = choice
    await query.edit_message_text(
        f"Ви обрали: {choice}. Надішліть свій молитовний намір текстом."
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    periodicity = context.user_data.get("periodicity", "не обрано")

    # Збереження у Google Sheets
    try:
        SHEET_PRAYER.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            update.effective_user.full_name,
            text,
            periodicity,
            update.effective_user.username or ""
        ])
        await update.message.reply_text("Ваш намір збережено! Дякуємо 🙏")
    except Exception as e:
        logger.error(f"Помилка збереження: {e}")
        await update.message.reply_text(
            "Сталася помилка при збереженні. Спробуйте пізніше."
        )

# --------------------------
# Create application
# --------------------------
def create_app():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(periodicity_handler, pattern="^(daily|weekly|monthly)$"))
    application.add_handler(CallbackQueryHandler(menu_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    @flask_app.route("/")
    def index():
        return "Bot is running ✅"

    @flask_app.route(WEBHOOK_PATH, methods=["POST"])
    def webhook():
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
            return "Unauth
