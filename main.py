import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from typing import Dict, List
import re

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class AanyaaBot:
    def __init__(self):
        # Get tokens from environment variables
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        if not self.telegram_token:
            logger.error("TELEGRAM_BOT_TOKEN not found")
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        if not self.gemini_api_key:
            logger.error("GEMINI_API_KEY not found")
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        logger.info("Both API keys found successfully")
        
        # Configure Google AI
        try:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            logger.info("Google AI configured successfully")
        except Exception as e:
            logger.error(f"Failed to configure Google AI: {e}")
            raise
        
        # Store conversation history
        self.user_conversations: Dict[int, List[str]] = {}
        
        # Aanyaa's personality
        self.personality_prompt = (
            "You are Aanyaa, a cute and friendly AI assistant girl. "
            "Be sweet, helpful, and use cute expressions occasionally. "
            "Add 'hehe' or emojis when appropriate. Always be warm and caring."
        )
    
    def should_respond_in_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if bot should respond in group chats"""
        message = update.message
        
        if message.chat.type == 'private':
            return True
        
        bot_username = context.bot.username.lower() if context.bot.username else "aanyaa"
        
        # Check mentions
        if message.entities:
            for entity in message.entities:
                if entity.type == 'mention':
                    mentioned = message.text[entity.offset:entity.offset + entity.length].lower()
                    if mentioned == f'@{bot_username}' or mentioned == '@aanyaa':
                        return True
        
        # Check replies
        if message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
            return True
        
        return False
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_name = update.effective_user.first_name or "friend"
        
        welcome_message = (
            f"Hi {user_name}! I'm **Aanyaa** 🌸\n\n"
            "I'm your cute AI assistant! Here's what I can help you with:\n\n"
            "💭 **Chat with me about anything!**\n"
            "✨ **Creative writing & storytelling**\n"
            "🧠 **Problem solving & questions**\n"
            "📚 **Learning & explanations**\n\n"
            "**In groups**: Tag me with @aanyaa or reply to my messages! 💕\n\n"
            "**Commands:**\n"
            "/start - See this intro\n"
            "/clear - Clear our chat history\n"
            "/help - Get help from me!\n\n"
            "Let's chat! What would you like to talk about? 😊"
        )
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user_name = update.effective_user.first_name or "friend"
        
        help_text = (
            f"Hey {user_name}! Let me help you~ 💕\n\n"
            "**How to chat with me:**\n"
            "🌸 **Private chat**: Just send me any message!\n"
            "🌸 **Group chat**: Tag me (@aanyaa) or reply to my messages\n\n"
            "**What I can do:**\n"
            "✨ Answer questions about anything\n"
            "✨ Help with coding and technical stuff\n"
            "✨ Creative writing and stories\n"
            "✨ Math and problem solving\n"
            "✨ Just chat and have fun!\n\n"
            "I'm here to help anytime! 😊"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "friend"
        
        self.user_conversations[user_id] = []
        await update.message.reply_text(
            f"Okayy {user_name}! ✨ I've cleared our conversation history. "
            "We can start fresh now! 😊"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        if not self.should_respond_in_group(update, context):
            return
        
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "friend"
        user_message = update.message.text
        
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = []
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        try:
            # Create prompt with personality
            prompt = f"{self.personality_prompt}\n\nUser's name: {user_name}\nUser's message: {user_message}"
            
            # Generate response
            response = self.model.generate_content(prompt)
            ai_response = response.text
            
            # Split long messages
            if len(ai_response) > 4000:
                chunks = [ai_response[i:i+4000] for i in range(0, len(ai_response), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(ai_response)
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            await update.message.reply_text(f"Oops {user_name}! 😅 I had a little hiccup there. Can you try again?")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Log errors"""
        logger.error(f"Update {update} caused error {context.error}")
    
    def run(self):
        """Start the bot"""
        # Create application
        application = Application.builder().token(self.telegram_token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("clear", self.clear_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Add error handler
        application.add_error_handler(self.error_handler)
        
        # Start the bot
        logger.info("Starting Aanyaa bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = AanyaaBot()
    bot.run()
