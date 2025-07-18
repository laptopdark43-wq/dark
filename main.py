import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from flask import Flask
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app for Render port binding
app = Flask(__name__)

@app.route('/')
def home():
    return "Aanyaa bot is running! 🌸"

@app.route('/health')
def health():
    return "OK"

class AanyaaBot:
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        if not self.telegram_token or not self.gemini_api_key:
            raise ValueError("Missing API keys")
        
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        logger.info("Bot initialized successfully")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_name = update.effective_user.first_name or "friend"
        await update.message.reply_text(
            f"Hi {user_name}! I'm Aanyaa 🌸\n\n"
            "I'm your cute AI assistant! Send me any message and I'll respond!\n\n"
            "In groups: Tag me @aanyaa or reply to my messages 💕"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_message = update.message.text
        user_name = update.effective_user.first_name or "friend"
        
        # Check if should respond in groups
        if update.message.chat.type != 'private':
            bot_username = context.bot.username
            if not (f'@{bot_username}' in user_message or 
                   (update.message.reply_to_message and 
                    update.message.reply_to_message.from_user.id == context.bot.id)):
                return
        
        try:
            prompt = f"You are Aanyaa, a cute and friendly AI assistant girl. Be sweet, helpful, and use cute expressions. User {user_name} says: {user_message}"
            response = self.model.generate_content(prompt)
            await update.message.reply_text(response.text)
        except Exception as e:
            logger.error(f"Error: {e}")
            await update.message.reply_text(f"Sorry {user_name}! 😅 I had a little error. Try again?")
    
    def run(self):
        app_telegram = Application.builder().token(self.telegram_token).build()
        app_telegram.add_handler(CommandHandler("start", self.start_command))
        app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("Starting Aanyaa bot...")
        app_telegram.run_polling()

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start Telegram bot
    bot = AanyaaBot()
    bot.run()
