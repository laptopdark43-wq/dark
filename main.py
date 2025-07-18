import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from typing import Dict, List

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramAIBot:
    def __init__(self):
        # Get tokens from environment variables
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        if not self.telegram_token or not self.gemini_api_key:
            raise ValueError("Please set TELEGRAM_BOT_TOKEN and GEMINI_API_KEY environment variables")
        
        # Configure Google AI
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Store conversation history for each user
        self.user_conversations: Dict[int, List[Dict]] = {}
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        welcome_message = (
            "🤖 **Welcome to Your AI Assistant!**\n\n"
            "I'm powered by Google Gemma 3 2B and I'm here to help you with:\n"
            "• Answering questions\n"
            "• Creative writing\n"
            "• Problem solving\n"
            "• General conversation\n\n"
            "Just send me any message and I'll respond!\n\n"
            "**Commands:**\n"
            "/start - Show this welcome message\n"
            "/clear - Clear conversation history\n"
            "/help - Show help information"
        )
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        
        # Initialize conversation history for new users
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = []
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🔧 **How to use this bot:**\n\n"
            "1. Just send me any message or question\n"
            "2. I'll respond using Google Gemma 3 2B AI\n"
            "3. I remember our conversation context\n\n"
            "**Available Commands:**\n"
            "/start - Welcome message\n"
            "/clear - Clear conversation history\n"
            "/help - Show this help\n\n"
            "**Tips:**\n"
            "• Be specific with your questions\n"
            "• I can help with coding, writing, math, and more\n"
            "• Use /clear if you want to start fresh"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command"""
        user_id = update.effective_user.id
        self.user_conversations[user_id] = []
        await update.message.reply_text("✅ Conversation history cleared! Starting fresh.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        user_id = update.effective_user.id
        user_message = update.message.text
        
        # Initialize conversation if not exists
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = []
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        try:
            # Add user message to conversation history
            self.user_conversations[user_id].append({
                'role': 'user',
                'parts': [user_message]
            })
            
            # Keep only last 10 exchanges to manage memory
            if len(self.user_conversations[user_id]) > 20:
                self.user_conversations[user_id] = self.user_conversations[user_id][-20:]
            
            # Create conversation context
            conversation_history = []
            for msg in self.user_conversations[user_id]:
                conversation_history.append({
                    'role': msg['role'],
                    'parts': msg['parts']
                })
            
            # Generate response using Gemini
            chat = self.model.start_chat(history=conversation_history[:-1])
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: chat.send_message(user_message)
            )
            
            ai_response = response.text
            
            # Add AI response to conversation history
            self.user_conversations[user_id].append({
                'role': 'model',
                'parts': [ai_response]
            })
            
            # Split long messages if needed
            if len(ai_response) > 4000:
                # Split into chunks of 4000 characters
                chunks = [ai_response[i:i+4000] for i in range(0, len(ai_response), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(ai_response)
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            error_message = (
                "❌ Sorry, I encountered an error while processing your message. "
                "Please try again in a moment."
            )
            await update.message.reply_text(error_message)
    
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
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = TelegramAIBot()
    bot.run()
