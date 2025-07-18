import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from flask import Flask
import threading
import json
from datetime import datetime

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
        
        # Enhanced memory system - stores last 10 chats per user (works in both private and group chats)
        self.user_memory = {}
        
        logger.info("Bot initialized successfully with enhanced memory system")
    
    def add_to_memory(self, user_id: int, user_message: str, bot_response: str, user_name: str, chat_type: str, chat_title: str = None):
        """Add conversation to user's memory (works for both private and group chats)"""
        if user_id not in self.user_memory:
            self.user_memory[user_id] = []
        
        # Add new conversation with chat context
        conversation = {
            'timestamp': datetime.now().isoformat(),
            'user_name': user_name,
            'user_message': user_message,
            'bot_response': bot_response,
            'chat_type': chat_type,
            'chat_title': chat_title if chat_title else 'Private Chat'
        }
        
        self.user_memory[user_id].append(conversation)
        
        # Keep only last 10 conversations per user
        if len(self.user_memory[user_id]) > 10:
            self.user_memory[user_id] = self.user_memory[user_id][-10:]
        
        logger.info(f"Added conversation to memory for user {user_id} ({user_name}) in {chat_type}. Total conversations: {len(self.user_memory[user_id])}")
    
    def get_memory_context(self, user_id: int, user_name: str) -> str:
        """Get memory context for the user (works across all chat types)"""
        if user_id not in self.user_memory or not self.user_memory[user_id]:
            return f"This is my first conversation with {user_name}."
        
        memory_context = f"My conversation history with {user_name}:\n"
        for i, conv in enumerate(self.user_memory[user_id], 1):
            chat_location = f"({conv['chat_title']})" if conv['chat_type'] != 'private' else "(Private)"
            memory_context += f"{i}. {chat_location} User: {conv['user_message'][:60]}{'...' if len(conv['user_message']) > 60 else ''}\n"
            memory_context += f"   My reply: {conv['bot_response'][:60]}{'...' if len(conv['bot_response']) > 60 else ''}\n"
        
        return memory_context
    
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
        user_id = update.effective_user.id
        
        # Check if user has previous conversations
        memory_info = ""
        if user_id in self.user_memory and self.user_memory[user_id]:
            memory_info = f"\n\n🧠 I remember our last {len(self.user_memory[user_id])} conversations across all chats! 😊"
        
        chat_type_info = "private chat" if update.message.chat.type == 'private' else f"group ({update.message.chat.title})"
        
        await update.message.reply_text(
            f"Hi {user_name}! I'm Aanyaa 🌸\n"
            f"Your cute AI assistant with advanced memory!\n\n"
            f"💕 **Private chats**: Just message me!\n"
            f"💕 **Groups**: Tag me @{context.bot.username or 'aanyaa'} or reply\n"
            f"🧠 **Memory**: I remember our last 10 chats in ALL locations!\n"
            f"📍 **Current location**: {chat_type_info}{memory_info}\n\n"
            f"What's up? 😊"
        )
    
    async def memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user their conversation memory across all chats"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "friend"
        
        if user_id not in self.user_memory or not self.user_memory[user_id]:
            await update.message.reply_text(f"Hey {user_name}! We haven't had any conversations yet. Start chatting with me! 😊")
            return
        
        memory_text = f"🧠 **Memory Bank for {user_name}**\n\n"
        memory_text += f"I remember our last {len(self.user_memory[user_id])} conversations:\n\n"
        
        for i, conv in enumerate(self.user_memory[user_id], 1):
            chat_location = f"📍 {conv['chat_title']}" if conv['chat_type'] != 'private' else "📍 Private Chat"
            memory_text += f"**{i}.** {chat_location}\n"
            memory_text += f"You: {conv['user_message'][:100]}{'...' if len(conv['user_message']) > 100 else ''}\n"
            memory_text += f"Me: {conv['bot_response'][:100]}{'...' if len(conv['bot_response']) > 100 else ''}\n\n"
        
        await update.message.reply_text(memory_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_message = update.message.text
        user_name = update.effective_user.first_name or "friend"
        user_id = update.effective_user.id
        chat_type = update.message.chat.type
        chat_title = update.message.chat.title if hasattr(update.message.chat, 'title') else None
        
        # Log the chat details
        logger.info(f"Received message from {user_name} (ID: {user_id}) in {chat_type}: {chat_title or 'Private'}")
        
        # Private chat - ALWAYS respond and remember
        if chat_type == 'private':
            logger.info(f"Processing private chat message from {user_name}")
            await self.generate_response(update, user_message, user_name, user_id, chat_type, chat_title)
            return
        
        # Group chat - only respond if tagged or replied to, but ALWAYS remember if responding
        if chat_type in ['group', 'supergroup']:
            logger.info(f"Processing group chat message from {user_name} in {chat_title}")
            
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
                await self.generate_response(update, cleaned_message, user_name, user_id, chat_type, chat_title)
            else:
                logger.info("Not responding to group message (not tagged or replied)")
    
    async def generate_response(self, update: Update, user_message: str, user_name: str, user_id: int, chat_type: str, chat_title: str = None):
        """Generate and send AI response with memory context"""
        try:
            # Check for special responses first
            special_response = self.check_special_responses(user_message, user_name)
            if special_response:
                await update.message.reply_text(special_response)
                # Add to memory
                self.add_to_memory(user_id, user_message, special_response, user_name, chat_type, chat_title)
                logger.info("Sent special response and added to memory")
                return
            
            # Get memory context for this specific user
            memory_context = self.get_memory_context(user_id, user_name)
            
            # Current chat context
            current_location = f"Currently in: {chat_title}" if chat_type != 'private' else "Currently in: Private Chat"
            
            # Enhanced personality prompt with memory
            prompt = f"""You are Aanyaa, a cute and friendly AI assistant girl with these personality traits:

MEMORY CONTEXT:
{memory_context}

CURRENT CONVERSATION:
{current_location}

IMPORTANT RESPONSE RULES:
- Keep responses to 2-3 lines maximum unless user asks you to elaborate
- Use casual phrases: "lol" for funny moments, "lmao" for very funny things
- If someone is being rude or irritating, you can use "bkl" (but only if they're really annoying)
- Be sweet but not overly formal
- Use emojis occasionally but don't overuse them
- Remember our previous conversations and refer to them when relevant
- You remember conversations from both private chats and group chats

PERSONALITY:
- Cute, friendly, and helpful
- Sometimes playful and funny
- Use expressions like "hehe" when appropriate
- Be caring but keep responses short and sweet

User {user_name} says: {user_message}

Remember: Keep it short (2-3 lines) unless they ask for more details! Use your memory of our previous conversations when relevant."""
            
            logger.info(f"Generating response with memory context for {user_name}: {user_message[:50]}...")
            response = self.model.generate_content(prompt)
            
            if response.text:
                await update.message.reply_text(response.text)
                # Add to memory
                self.add_to_memory(user_id, user_message, response.text, user_name, chat_type, chat_title)
                logger.info(f"Response sent successfully and added to memory for {user_name}")
            else:
                error_response = f"Sorry {user_name}! 😅 I didn't get that. Try again?"
                await update.message.reply_text(error_response)
                self.add_to_memory(user_id, user_message, error_response, user_name, chat_type, chat_title)
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            error_response = f"Oops {user_name}! 😅 Something went wrong. Try again?"
            await update.message.reply_text(error_response)
            self.add_to_memory(user_id, user_message, error_response, user_name, chat_type, chat_title)
    
    def run(self):
        app_telegram = Application.builder().token(self.telegram_token).build()
        app_telegram.add_handler(CommandHandler("start", self.start_command))
        app_telegram.add_handler(CommandHandler("memory", self.memory_command))
        app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("Starting enhanced Aanyaa bot with universal memory system...")
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
