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

# ---------------------- Налаштування ----------------------
TOKEN = os.getenv("BOT_TOKEN", "8321988283:AAGjmdxmOoOixeYFLNUUtZ1XfknOuGklX1U")
SPREADSHEET_ID = "1lJc616p6Mx0QBAXexmBJxYX9cte8cSBANJQNaR2V12w"
ADMIN_CHAT_ID = 460841825
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")  # автоматично підставляється Render

# ---------------------- Логування -------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------- Google Sheets ---------------------
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

# ---------------------- Основна клавіатура ----------------
def main_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🙏 Залишити намірення", callback_data="pray_request")],
            [InlineKeyboardButton("✝️ Приєднатись до молитви", callback_data="pray_for_others")],
            [InlineKeyboardButton("🛡️ Більше про Круціяту Визволення Людини", callback_data="crusade")],
        ]
    )

# ---------------------- Обробники --------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Слава Ісусу Христу!\n\n"
        "Це сторінка молитовної ініціативи Круціяти Визволення Людини 🔥Смолоскипи Гедеона🔥\n\n"
        "Тут Ви можете:\n"
        "🙏 Залишити намірення за ЗВІЛЬНЕННЯ ЛЮДИНИ ІЗ ЗАЛЕЖНОСТІ\n"
        "✝️ Приєднатись до молитви за залежних осіб\n"
        "🛡️ Дізнатись більше про Круціяту Визволення Людини\n\n"
        "Тож, розпочнімо!",
        reply_markup=main_keyboard(),
    )

async def periodicity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mapping = {"daily": "Щодня", "weekly": "Щотижня", "monthly": "Щомісяця"}
    context.user_data["periodicity"] = mapping.get(query.data, query.data)
    context.user_data["step_others"] = 4
    await query.message.reply_text("Дякуємо! 🙏\nЗалиште телефон або напишіть «–»:")

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "pray_request":
        context.user_data.clear()
        context.user_data["step"] = 1
        await query.message.reply_text("Введіть ім’я людини, за яку просите молитву:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]))
    elif data == "pray_for_others":
        context.user_data.clear()
        context.user_data["step_others"] = 1
        await query.message.reply_text("Введіть своє ім’я 🙏", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]))
    elif data == "back":
        context.user_data.clear()
        await query.message.reply_text("Головне меню:", reply_markup=main_keyboard())

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if context.user_data.get("step") == 1:
        SHEET_PRAYER.append_row([timestamp, text])
        await update.message.reply_text("Дякуємо! 🙏 Намірення додано.", reply_markup=main_keyboard())
        context.user_data.clear()
        return

    step_others = context.user_data.get("step_others")
    if step_others:
        if step_others == 1:
            context.user_data["name"] = text
            context.user_data["step_others"] = 2
            await update.message.reply_text("Яку молитву бажаєте молитися?")
            return
        if step_others == 2:
            context.user_data["prayer"] = text
            context.user_data["step_others"] = 3
            await update.message.reply_text(
                "Як часто будете молитися?", 
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Щодня", callback_data="daily")],
                    [InlineKeyboardButton("Щотижня", callback_data="weekly")],
                    [InlineKeyboardButton("Щомісяця", callback_data="monthly")]
                ])
            )
            return
        if step_others == 4:
            phone = text if text else "-"
            SHEET_OTHERS.append_row([
                timestamp,
                context.user_data.get("name", "-"),
                context.user_data.get("prayer", "-"),
                context.user_data.get("periodicity", "-"),
                phone
            ])
            await update.message.reply_text("✅ Дякуємо за участь у молитві 🙏", reply_markup=main_keyboard())
            context.user_data.clear()
            return

    await update.message.reply_text("Оберіть дію:", reply_markup=main_keyboard())

# ---------------------- Flask + Webhook -------------------
app = Flask(__name__)

async def setup_webhook(application: Application):
    await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

@app.route("/")
def home():
    return "✅ Bot is running!", 200

if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(periodicity_handler, pattern="^(daily|weekly|monthly)$"))
    application.add_handler(CallbackQueryHandler(menu_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_webhook(application))

    # Flask запускається на Render (порт 10000 або змінний)
    port = int(os.getenv("PORT", 10000))
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

    application.run_polling(stop_signals=None)
