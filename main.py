import os
import logging
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import requests

# Setup logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(_name_)

# Load tokens
TELEGRAM_TOKEN = os.getenv("7208370023:AAEvk7C9sAqIgdNym9fFXmpZswYoXhvjqZE")
GEMINI_API_KEY = os.getenv("AIzaSyCh8Hq3wAy2Y_FhKbJv-NjSniQJZWMMXxU")

# Gemini API request function
def chat_with_gemini(prompt):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0:generateContent"
    headers = {
        "Content-Type": "application/json"
    }
    params = {
        "key": AIzaSyCh8Hq3wAy2Y_FhKbJv-NjSniQJZWMMXxU
    }
    body = {
        "contents": [
            {"parts": [{"text": f"You are Aanyaa, a sweet and flirty girl. Reply cutely and fun:\n{prompt}"}]}
        ]
    }
    try:
        res = requests.post(url, headers=headers, params=params, json=body)
        res.raise_for_status()
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return "Oops cutie, I can't think right now~ 💫"

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Private chat OR tagged in group OR replied to Aanyaa
    is_private = message.chat.type == "private"
    is_tagged = context.bot.username in message.text if message.text else False
    is_reply = message.reply_to_message and message.reply_to_message.from_user.username == context.bot.username

    if is_private or is_tagged or is_reply:
        user_input = message.text or ""
        response = chat_with_gemini(user_input)
        await message.reply_text(response)

# Start bot
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.run_polling()

if _name_ == "_main_":
    import asyncio
    asyncio.run(main())
