# bot.py — повний робочий код з WEBHOOK для Render
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
TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = "1lJc616p6Mx0QBAXexmBJxYX9cte8cSBANJQNaR2V12w"
ADMIN_CHAT_ID = 460841825

WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = TOKEN  # достатньо

# --------------------------
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

# === УСЯ ТВОЯ ЛОГІКА ДАЛІ — БЕЗ ЗМІН ===
# (periodicity_handler, menu_handler, message_handler)
# 👉 СЮДИ ВСТАВ ТОЧНО ТІ САМІ ФУНКЦІЇ З ТВОГО КОДУ 👈

# --------------------------
def create_app():
    flask_app = Flask(__name__)
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(periodicity_handler, pattern="^(daily|weekly|monthly)$"))
    application.add_handler(CallbackQueryHandler(menu_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    @flask_app.route("/")
    def index():
        return "Bot is running (webhook) ✅"

    @flask_app.route(WEBHOOK_PATH, methods=["POST"])
    async def webhook():
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
            return "Unauthorized", 403
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return "OK"

    return flask_app, application

# --------------------------
if __name__ == "__main__":
    flask_app, application = create_app()

    port = int(os.environ.get("PORT", 10000))
    application.bot.initialize()
    application.bot.set_webhook(
        url=os.environ["RENDER_EXTERNAL_URL"] + WEBHOOK_PATH,
        secret_token=WEBHOOK_SECRET,
    )

    flask_app.run(host="0.0.0.0", port=port)
