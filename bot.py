import os
import logging
import gspread
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from google.oauth2.service_account import Credentials

# -------------------
# Налаштування логів
# -------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# -------------------
# Налаштування Telegram
# -------------------
TOKEN = os.environ.get("BOT_TOKEN")      # Render Environment
URL = os.environ.get("APP_URL")          # Render URL: https://your-app.onrender.com
PORT = int(os.environ.get("PORT", 10000))

# -------------------
# Налаштування Google Sheets
# -------------------
# JSON ключ сервісного акаунта зберігаємо у Render як змінну BOT_CREDS_JSON
creds_json = os.environ.get("BOT_CREDS_JSON")

if not creds_json:
    raise ValueError("Не задано BOT_CREDS_JSON!")

credentials = Credentials.from_service_account_info(
    eval(creds_json),  # перетворюємо рядок у dict
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

gc = gspread.authorize(credentials)
SPREADSHEET_NAME = "PrayerIntents"  # Назва вашого Google Sheet
sheet = gc.open(SPREADSHEET_NAME).sheet1

# -------------------
# Flask app
# -------------------
flask_app = Flask(__name__)

# -------------------
# Telegram Handlers
# -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Щодня", callback_data="daily"),
            InlineKeyboardButton("Щотижня", callback_data="weekly"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привіт! Оберіть періодичність молитов:", reply_markup=reply_markup
    )

async def periodicity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    context.user_data["periodicity"] = choice
    await query.edit_message_text(
        text=f"Ви обрали: {choice}. Надішліть свій молитовний намір текстом."
    )

async def intent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intent_text = update.message.text
    periodicity = context.user_data.get("periodicity", "не обрано")

    # Збереження в Google Sheets
    try:
        sheet.append_row([update.effective_user.id, update.effective_user.username,
                          intent_text, periodicity])
        await update.message.reply_text("Ваш намір збережено! Дякуємо 🙏")
    except Exception as e:
        logging.error(f"Помилка збереження: {e}")
        await update.message.reply_text("Сталася помилка при збереженні. Спробуйте пізніше.")

# -------------------
# Telegram Application
# -------------------
application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(periodicity_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, intent_handler))

# -------------------
# Flask route для webhook
# -------------------
@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK"

# -------------------
# Запуск Flask і встановлення webhook
# -------------------
if __name__ == "__main__":
    import telegram

    bot = telegram.Bot(token=TOKEN)
    bot.set_webhook(f"{URL}/{TOKEN}")  # Telegram буде надсилати POST сюди

    flask_app.run(host="0.0.0.0", port=PORT)
