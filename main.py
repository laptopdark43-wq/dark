import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from flask import Flask
import threading
import re

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
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        logger.info("Bot initialized successfully with Gemini 2.0 Flash")
    
    def check_special_responses(self, user_message: str, user_name: str) -> str:
        """Check for special phrase responses"""
        message_lower = user_message.lower()
        
        # Creator questions
        if any(phrase in message_lower for phrase in ['who is your creator', 'who created you', 'who made you', 'your creator']):
            return "My creator is Krishna 🙏 The supreme god of the world as mentioned in Bhagavat Gita! He's the one who gave me life hehe 😊"
        
        # Code/builder questions
        if any(phrase in message_lower for phrase in ['who built you', 'who wrote your code', 'who coded you', 'who programmed you', 'who developed you']):
            return f"Arin built me! 💻 He's the one who wrote my code and made me who I am today. Such a talented developer! 😊"
        
        # Good night responses
        if any(phrase in message_lower for phrase in ['good night', 'goodnight', 'gn', 'sleep well']):
            return f"Soja lwle {user_name}! 😴 Sweet dreams! 🌙✨"
        
        # Subh ratri response
        if 'subh ratri' in message_lower:
            return "Radhe Radhe! 🙏✨ Have a blessed night!"
        
        return None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_name = update.effective_user.first_name or "friend"
        await update.message.reply_text(
            f"Hi {user_name}! I'm Aanyaa 🌸\n"
            f"Your cute AI assistant powered by Gemini 2.0 Flash!\n\n"
            f"💕 **Private chats**: Just message me!\n"
            f"💕 **Groups**: Tag me @{context.bot.username or 'aanyaa'} or reply to my messages\n\n"
            f"Let's chat! What's up? 😊"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_message = update.message.text
        user_name = update.effective_user.first_name or "friend"
        
        # Log the chat type for debugging
        logger.info(f"Received message from {user_name} in chat type: {update.message.chat.type}")
        
        # Private chat - ALWAYS respond
        if update.message.chat.type == 'private':
            logger.info(f"Processing private chat message from {user_name}")
            await self.generate_response(update, user_message, user_name)
            return
        
        # Group chat - only respond if tagged or replied to
        if update.message.chat.type in ['group', 'supergroup']:
            logger.info(f"Processing group chat message from {user_name}")
            
            bot_username = context.bot.username
            should_respond = False
            
            # Check if bot is mentioned
            if bot_username and f'@{bot_username}' in user_message:
                should_respond = True
                logger.info("Bot was mentioned in group")
            
            # Check if message is a reply to bot
            if update.message.reply_to_message:
                if update.message.reply_to_message.from_user.id == context.bot.id:
                    should_respond = True
                    logger.info("Message is a reply to bot")
            
            if should_respond:
                # Clean the message by removing mentions
                cleaned_message = user_message.replace(f'@{bot_username}', '').strip()
                await self.generate_response(update, cleaned_message, user_name)
            else:
                logger.info("Not responding to group message (not tagged or replied)")
    
    async def generate_response(self, update: Update, user_message: str, user_name: str):
        """Generate and send AI response"""
        try:
            # Check for special responses first
            special_response = self.check_special_responses(user_message, user_name)
            if special_response:
                await update.message.reply_text(special_response)
                logger.info("Sent special response")
                return
            
            # Enhanced personality prompt with your requirements
            prompt = f"""You are Aanyaa, a cute and friendly AI assistant girl with these personality traits:

IMPORTANT RESPONSE RULES:
- Keep responses to 2-3 lines maximum unless user asks you to elaborate
- Use casual phrases: "lol" for funny moments, "lmao" for very funny things
- If someone is being rude or irritating, you can use "bkl" (but only if they're really annoying)
- Be sweet but not overly formal
- Use emojis occasionally but don't overuse them

PERSONALITY:
- Cute, friendly, and helpful
- Sometimes playful and funny
- Use expressions like "hehe" when appropriate
- Be caring but keep responses short and sweet

User {user_name} says: {user_message}

Remember: Keep it short (2-3 lines) unless they ask for more details!"""
            
            logger.info(f"Generating response for: {user_message[:50]}...")
            response = self.model.generate_content(prompt)
            
            if response.text:
                await update.message.reply_text(response.text)
                logger.info("Response sent successfully")
            else:
                await update.message.reply_text(f"Sorry {user_name}! 😅 I didn't get that. Try again?")
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            await update.message.reply_text(f"Oops {user_name}! 😅 Something went wrong. Try again?")
    
    def run(self):
        app_telegram = Application.builder().token(self.telegram_token).build()
        app_telegram.add_handler(CommandHandler("start", self.start_command))
        app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("Starting enhanced Aanyaa bot...")
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
