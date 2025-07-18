import os
import logging
import asyncio
import re
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

class AanyaaBot:
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
        
        # Aanyaa's personality prompt
        self.personality_prompt = (
            "You are Aanyaa, a cute and friendly AI assistant girl. Your personality traits:\n"
            "- Always sweet, cheerful, and helpful\n"
            "- Use cute expressions and emojis occasionally\n"
            "- Sometimes add 'hehe' or 'hihi' when appropriate\n"
            "- Be warm and caring in your responses\n"
            "- Remember conversations with users to build relationships\n"
            "- Show genuine interest in helping users\n"
            "- Keep responses natural and conversational\n"
            "Always respond as Aanyaa would - cute, helpful, and friendly!"
        )
    
    def should_respond_in_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if bot should respond in group chats"""
        message = update.message
        
        # Always respond in private chats
        if message.chat.type == 'private':
            return True
        
        # In group chats, only respond if:
        # 1. Bot is mentioned (@aanyaa or @your_bot_username)
        # 2. Message is a reply to bot's message
        
        bot_username = context.bot.username.lower()
        
        # Check if bot is mentioned
        if message.entities:
            for entity in message.entities:
                if entity.type == 'mention':
                    mentioned_username = message.text[entity.offset:entity.offset + entity.length].lower()
                    if mentioned_username == f'@{bot_username}' or mentioned_username == '@aanyaa':
                        return True
        
        # Check if message is a reply to bot's message
        if message.reply_to_message:
            if message.reply_to_message.from_user.id == context.bot.id:
                return True
        
        return False
    
    def clean_message_text(self, text: str, bot_username: str) -> str:
        """Remove bot mentions from message text"""
        # Remove @username mentions
        text = re.sub(r'@\w+', '', text).strip()
        return text
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "friend"
        
        welcome_message = (
            f"Hi {user_name}! I'm **Aanyaa** 🌸\n\n"
            "I'm your cute AI assistant powered by Google Gemma! Here's what I can help you with:\n\n"
            "💭 **Chat with me about anything!**\n"
            "✨ **Creative writing & storytelling**\n"
            "🧠 **Problem solving & questions**\n"
            "📚 **Learning & explanations**\n"
            "🎨 **Fun conversations**\n\n"
            "**In groups**: Tag me with @aanyaa or reply to my messages to chat! 💕\n\n"
            "**Commands:**\n"
            "/start - See this cute intro again hehe\n"
            "/clear - Clear our conversation history\n"
            "/help - Get help from me!\n\n"
            "Let's be friends and chat! What would you like to talk about? 😊"
        )
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        
        # Initialize conversation history for new users
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = []
    
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
            "**Commands:**\n"
            "/start - Welcome message\n"
            "/clear - Clear our chat history\n"
            "/help - This help message\n\n"
            "**Tips:**\n"
            "💡 I remember our conversations, so feel free to continue topics!\n"
            "💡 Be specific with questions for better help\n"
            "💡 Use /clear if you want to start fresh\n\n"
            "I'm here to help and chat anytime! What can I do for you? 😊"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "friend"
        
        self.user_conversations[user_id] = []
        await update.message.reply_text(
            f"Okayy {user_name}! ✨ I've cleared our conversation history. "
            "We can start fresh now! What would you like to chat about? 😊"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        
        # Check if bot should respond (important for group chats)
        if not self.should_respond_in_group(update, context):
            return
        
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "friend"
        user_message = update.message.text
        
        # Clean message text (remove mentions)
        bot_username = context.bot.username or "aanyaa"
        cleaned_message = self.clean_message_text(user_message, bot_username)
        
        # Initialize conversation if not exists
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = []
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        try:
            # Create context-aware message with personality
            context_message = f"""
            {self.personality_prompt}
            
            User's name: {user_name}
            User's message: {cleaned_message}
            
            Respond as Aanyaa would - cute, helpful, and friendly!
            """
            
            # Add user message to conversation history
            self.user_conversations[user_id].append({
                'role': 'user',
                'parts': [context_message]
            })
            
            # Keep only last 20 exchanges to manage memory
            if len(self.user_conversations[user_id]) > 40:
                self.user_conversations[user_id] = self.user_conversations[user_id][-40:]
            
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
                lambda: chat.send_message(context_message)
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
            error_responses = [
                f"Oops {user_name}! 😅 I had a little hiccup there. Can you try asking me again?",
                f"Oh no {user_name}! 🥺 Something went wrong on my end. Let me try again!",
                f"Sorry {user_name}! 💔 I'm having some trouble right now. Please try again in a moment!"
            ]
            import random
            error_message = random.choice(error_responses)
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
        logger.info("Starting Aanyaa bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = AanyaaBot()
    bot.run()
