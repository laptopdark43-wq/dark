import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from flask import Flask
import threading
import asyncio
from datetime import datetime
import random
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
        logger.info("=== Bot Initialization Starting ===")
        
        # Get environment variables
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.a4f_api_key = os.getenv('A4F_API_KEY')
        
        # Enhanced logging for debugging
        logger.info(f"Telegram token present: {bool(self.telegram_token)}")
        logger.info(f"A4F API key present: {bool(self.a4f_api_key)}")
        logger.info(f"A4F API key length: {len(self.a4f_api_key) if self.a4f_api_key else 0}")
        
        # Better error handling with specific messages
        if not self.telegram_token:
            logger.error("❌ TELEGRAM_BOT_TOKEN missing!")
            raise ValueError("TELEGRAM_BOT_TOKEN required")
        
        if not self.a4f_api_key:
            logger.error("❌ A4F_API_KEY missing!")
            raise ValueError("A4F_API_KEY required")
        
        logger.info("✅ All environment variables found")
        
        # Initialize OpenAI client with A4F API
        try:
            self.client = OpenAI(
                api_key=self.a4f_api_key,
                base_url="https://api.a4f.co/v1"
            )
            logger.info("✅ OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            raise
        
        # Memory system - stores last 10 chats per user
        self.user_memory = {}
        
        # PFP rating history - stores ratings given by users
        self.pfp_ratings = {}
        
        # Future prediction history - stores predictions made
        self.predictions = {}
        
        logger.info("✅ Bot initialized successfully with PFP Rating, Future Prediction, and Natural Choice features")
    
    def add_to_memory(self, user_id: int, user_message: str, bot_response: str, user_name: str, chat_type: str, chat_title: str = None):
        """Add conversation to user's memory"""
        if user_id not in self.user_memory:
            self.user_memory[user_id] = []
        
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
        
        logger.info(f"Added conversation to memory for user {user_id} ({user_name})")
    
    def get_memory_context(self, user_id: int, user_name: str) -> str:
        """Get memory context for the user"""
        if user_id not in self.user_memory or not self.user_memory[user_id]:
            return f"This is my first conversation with {user_name}."
        
        memory_context = f"My conversation history with {user_name}:\n"
        for i, conv in enumerate(self.user_memory[user_id], 1):
            chat_location = f"({conv['chat_title']})" if conv['chat_type'] != 'private' else "(Private)"
            memory_context += f"{i}. {chat_location} User: {conv['user_message'][:60]}{'...' if len(conv['user_message']) > 60 else ''}\n"
            memory_context += f"   My reply: {conv['bot_response'][:60]}{'...' if len(conv['bot_response']) > 60 else ''}\n"
        
        return memory_context
    
    # PFP Rating System
    def generate_pfp_rating(self, user_name: str) -> dict:
        """Generate a random but consistent PFP rating with reasons"""
        # Generate a rating between 1-100
        rating = random.randint(1, 100)
        
        # Rating categories with reasons
        if rating >= 90:
            reasons = [
                "Your pfp has amazing aesthetic vibes! ✨",
                "The composition is absolutely perfect! 📸",
                "You look stunning and confident! 💫",
                "The lighting and quality are chef's kiss! 😘",
                "Your style is totally on point! 👌"
            ]
            category = "Absolutely Amazing!"
        elif rating >= 80:
            reasons = [
                "Really good choice! Love the vibe! 😊",
                "Great quality and nice expression! 👍",
                "You look really good in this one! 💕",
                "Nice background and composition! 🎨",
                "Your smile is so genuine! 😄"
            ]
            category = "Really Good!"
        elif rating >= 70:
            reasons = [
                "Pretty nice! Could use better lighting though 💡",
                "Good pic but the angle could be better 📐",
                "Nice but maybe try a different background? 🖼️",
                "Decent quality, you look good! 👌",
                "Not bad! The colors work well together 🎨"
            ]
            category = "Pretty Good"
        elif rating >= 60:
            reasons = [
                "It's okay but could be more creative 🎭",
                "Average quality, try better lighting next time 💡",
                "Not bad but you can do better! 📸",
                "The composition needs some work 🖼️",
                "It's fine but lacks that wow factor ✨"
            ]
            category = "Average"
        else:
            reasons = [
                "Hmm, maybe try a new angle? 📐",
                "Could use better quality and lighting 💡",
                "Time for a pfp update! 🔄",
                "The background is a bit distracting 🖼️",
                "You deserve a better pfp than this! 💕"
            ]
            category = "Needs Improvement"
        
        reason = random.choice(reasons)
        
        return {
            'rating': rating,
            'category': category,
            'reason': reason
        }
    
    def detect_pfp_rating_request(self, message: str) -> bool:
        """Detect if user is asking for PFP rating"""
        message_lower = message.lower()
        
        pfp_keywords = [
            'rate my pfp', 'rate my profile picture', 'rate my dp', 'rate my pic',
            'how is my pfp', 'how is my profile picture', 'how is my dp',
            'what do you think of my pfp', 'what do you think of my profile picture',
            'rate my avatar', 'how do i look', 'rate my photo'
        ]
        
        return any(keyword in message_lower for keyword in pfp_keywords)
    
    # Future Prediction System
    def generate_future_prediction(self, query: str, user_name: str) -> dict:
        """Generate future prediction with probability"""
        # Generate probability between 1-100
        probability = random.randint(1, 100)
        
        # Prediction templates based on probability ranges
        if probability >= 85:
            confidence = "Very High"
            prediction_templates = [
                "I'm really confident this will happen! ✨",
                "The signs are all pointing to yes! 🌟",
                "I have a really good feeling about this! 💫",
                "This is very likely to come true! 🎯",
                "The universe is aligning for this! 🌌"
            ]
        elif probability >= 70:
            confidence = "High"
            prediction_templates = [
                "This has a good chance of happening! 👍",
                "I'm feeling positive about this! 😊",
                "The odds are in your favor! 🍀",
                "This looks promising! ✨",
                "I can see this working out! 👌"
            ]
        elif probability >= 50:
            confidence = "Moderate"
            prediction_templates = [
                "This could go either way! 🤔",
                "It's possible but not guaranteed! 🎲",
                "The future is a bit unclear on this one! 🔮",
                "There's a decent chance! 🤞",
                "It depends on many factors! ⚖️"
            ]
        elif probability >= 30:
            confidence = "Low"
            prediction_templates = [
                "This might be challenging! 😅",
                "The odds are a bit against you! 😬",
                "It's possible but unlikely! 🎭",
                "You might need to work harder for this! 💪",
                "This one's a bit tricky! 🤯"
            ]
        else:
            confidence = "Very Low"
            prediction_templates = [
                "This is quite unlikely! 😅",
                "The chances are pretty slim! 😬",
                "You might want to have a backup plan! 🎭",
                "This one's really tough! 😰",
                "The universe says 'probably not'! 🌌"
            ]
        
        prediction = random.choice(prediction_templates)
        
        return {
            'probability': probability,
            'confidence': confidence,
            'prediction': prediction,
            'query': query
        }
    
    def detect_future_prediction_request(self, message: str) -> str:
        """Detect if user is asking for future prediction"""
        message_lower = message.lower()
        
        # Common prediction patterns
        patterns = [
            r'will i (.+)',
            r'what are my chances of (.+)',
            r'predict (.+)',
            r'what will happen (.+)',
            r'future of (.+)',
            r'probability of (.+)',
            r'chances of (.+)',
            r'will (.+) happen',
            r'is (.+) going to happen',
            r'predict my future',
            r'what does the future hold',
            r'fortune telling',
            r'crystal ball'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                if match.groups():
                    return match.group(1).strip()
                else:
                    return "your future"
        
        # Check for general future keywords
        future_keywords = [
            'future', 'predict', 'probability', 'chances', 'will happen',
            'crystal ball', 'fortune', 'destiny', 'fate'
        ]
        
        if any(keyword in message_lower for keyword in future_keywords):
            return "your future"
        
        return None
    
    # NEW: Natural Choice Selection System
    def detect_choice_request(self, message: str) -> dict:
        """Detect natural choice requests in conversation"""
        message_lower = message.lower()
        
        # Natural conversation patterns for choices
        natural_patterns = [
            # Direct questions
            'should i', 'what should i', 'which should i', 'which one should i',
            'help me choose', 'help me decide', 'what do you think',
            'which is better', 'which would you pick', 'what would you choose',
            
            # Casual expressions
            'idk what to', "don't know what to", 'cant decide', "can't decide",
            'confused between', 'torn between', 'stuck between',
            
            # Comparison words
            ' or ', ' vs ', ' versus ', 'either', 'both are'
        ]
        
        # Check if message contains choice indicators
        has_choice_pattern = any(pattern in message_lower for pattern in natural_patterns)
        
        if has_choice_pattern or '?' in message:
            options = []
            
            # Extract options using multiple methods
            
            # Method 1: "A or B" pattern
            or_pattern = r'(?:between\s+|choose\s+)?([^?]+?)\s+or\s+([^?]+?)(?:\?|$|\.)'
            or_match = re.search(or_pattern, message, re.IGNORECASE)
            if or_match:
                option1 = or_match.group(1).strip()
                option2 = or_match.group(2).strip()
                # Clean up common prefixes
                for prefix in ['should i ', 'to ', 'the ', 'a ']:
                    option1 = option1.replace(prefix, '')
                    option2 = option2.replace(prefix, '')
                options = [option1, option2]
            
            # Method 2: List with commas "A, B, or C"
            if not options:
                comma_pattern = r'(?:between\s+|choose\s+)?([^?]+?)(?:,\s*(?:or\s+)?([^?]+?))+(?:\?|$|\.)'
                comma_match = re.search(comma_pattern, message, re.IGNORECASE)
                if comma_match and ',' in message:
                    # Split by comma and 'or'
                    text_part = comma_match.group(0)
                    parts = re.split(r',\s*(?:or\s+)?|or\s+', text_part)
                    options = [part.strip() for part in parts if part.strip() and not any(word in part.lower() for word in ['should', 'choose', 'between'])]
            
            # Method 3: Simple "A vs B" or "A versus B"
            if not options:
                vs_pattern = r'([^?]+?)\s+(?:vs|versus)\s+([^?]+?)(?:\?|$|\.)'
                vs_match = re.search(vs_pattern, message, re.IGNORECASE)
                if vs_match:
                    options = [vs_match.group(1).strip(), vs_match.group(2).strip()]
            
            # Method 4: "either A or B"
            if not options:
                either_pattern = r'either\s+([^?]+?)\s+or\s+([^?]+?)(?:\?|$|\.)'
                either_match = re.search(either_pattern, message, re.IGNORECASE)
                if either_match:
                    options = [either_match.group(1).strip(), either_match.group(2).strip()]
            
            # Clean up options
            if options:
                cleaned_options = []
                for option in options:
                    # Remove common question words and prefixes
                    option = re.sub(r'^(should i |to |the |a |an |go |do |eat |watch |play |buy )', '', option, flags=re.IGNORECASE)
                    option = option.strip('.,?!')
                    if option and len(option) > 1:
                        cleaned_options.append(option)
                
                if len(cleaned_options) >= 2:
                    return {
                        'is_choice': True,
                        'options': cleaned_options,
                        'original_message': message
                    }
        
        return {'is_choice': False}
    
    def make_choice(self, options: list, user_name: str) -> str:
        """Make a natural, casual choice like a friend would"""
        if not options or len(options) < 2:
            return None
        
        chosen_option = random.choice(options)
        
        # Casual, natural responses like a friend would give
        casual_responses = [
            f"Go with {chosen_option}!",
            f"I'd pick {chosen_option} tbh",
            f"{chosen_option} for sure!",
            f"Definitely {chosen_option} lol",
            f"{chosen_option}! No doubt",
            f"Easy - {chosen_option}!",
            f"{chosen_option} is the move!",
            f"I'm feeling {chosen_option}",
            f"{chosen_option} all the way!",
            f"Trust me, {chosen_option}!"
        ]
        
        # Sometimes add a casual reason (50% chance)
        if random.randint(1, 100) > 50:
            casual_reasons = [
                "just feels right",
                "trust me on this one", 
                "it's giving good vibes",
                "better choice honestly",
                "you'll thank me later",
                "just go for it",
                "why not right?",
                "sounds more fun",
                "better option imo"
            ]
            
            base_response = random.choice(casual_responses)
            reason = random.choice(casual_reasons)
            return f"{base_response} - {reason} hehe"
        else:
            return random.choice(casual_responses)
    
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
    
    async def get_openai_response(self, prompt: str) -> str:
        """Get response from OpenAI A4F API using Gemini 2.5 Flash"""
        try:
            logger.info("🔄 Making API call to A4F...")
            loop = asyncio.get_event_loop()
            
            def sync_call():
                completion = self.client.chat.completions.create(
                    model="provider-3/gemini-2.0-flash",
                    messages=[{"role": "user", "content": prompt}],
                    timeout=30
                )
                return completion.choices[0].message.content
            
            response = await loop.run_in_executor(None, sync_call)
            logger.info("✅ API call successful")
            return response
            
        except Exception as e:
            logger.error(f"❌ Detailed API error: {type(e).__name__}: {str(e)}")
            return "I'm having trouble thinking right now 😅 Try again in a moment!"
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_name = update.effective_user.first_name or "friend"
        user_id = update.effective_user.id
        
        # Check if user has previous conversations
        memory_info = ""
        if user_id in self.user_memory and self.user_memory[user_id]:
            memory_info = f"\n\n🧠 I remember our last {len(self.user_memory[user_id])} conversations!"
        
        chat_type_info = "private chat" if update.message.chat.type == 'private' else f"group ({update.message.chat.title})"
        
        await update.message.reply_text(
            f"Hi {user_name}! I'm Aanyaa 🌸\n"
            f"Your cute AI assistant with special powers!\n\n"
            f"💕 **Private chats**: Just message me!\n"
            f"💕 **Groups**: Tag me @{context.bot.username or 'aanyaa'} or reply\n"
            f"🧠 **Memory**: I remember our last 10 chats!\n\n"
            f"**✨ Special Features:**\n"
            f"📸 **PFP Rating**: Ask me to \"rate my pfp\" for honest feedback!\n"
            f"🔮 **Future Predictions**: Ask me to predict anything with probability!\n"
            f"🤔 **Natural Choice Maker**: I'll choose from any options naturally!\n\n"
            f"**Commands:**\n"
            f"📸 `/ratepfp` - Rate your profile picture\n"
            f"🔮 `/predict` - Ask for future predictions\n"
            f"🤔 `/choose` - Make a choice from options\n"
            f"🧠 `/memory` - View chat history\n"
            f"🧹 `/clear` - Clear memory\n"
            f"❓ `/help` - Get help\n\n"
            f"**Natural Examples:**\n"
            f"📸 \"Rate my profile picture please!\"\n"
            f"🔮 \"Will I pass my exam?\" or \"Predict my future!\"\n"
            f"🤔 \"Should I eat pizza or burger?\" or \"Can't decide between studying or sleeping\"\n\n"
            f"📍 **Current location**: {chat_type_info}{memory_info}\n\n"
            f"What's up? 😊"
        )
    
    async def ratepfp_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Rate user's profile picture"""
        user_name = update.effective_user.first_name or "friend"
        user_id = update.effective_user.id
        
        # Generate PFP rating
        rating_data = self.generate_pfp_rating(user_name)
        
        # Store rating in history
        if user_id not in self.pfp_ratings:
            self.pfp_ratings[user_id] = []
        
        self.pfp_ratings[user_id].append({
            'rating': rating_data['rating'],
            'category': rating_data['category'],
            'reason': rating_data['reason'],
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 5 ratings
        if len(self.pfp_ratings[user_id]) > 5:
            self.pfp_ratings[user_id] = self.pfp_ratings[user_id][-5:]
        
        await update.message.reply_text(
            f"📸 **PFP Rating for {user_name}** 📸\n\n"
            f"🎯 **Rating**: {rating_data['rating']}/100\n"
            f"📊 **Category**: {rating_data['category']}\n\n"
            f"💭 **My thoughts**: {rating_data['reason']}\n\n"
            f"🌸 *Remember, beauty is subjective and you're amazing regardless! hehe* 😊"
        )
    
    async def predict_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Make future predictions"""
        user_name = update.effective_user.first_name or "friend"
        user_id = update.effective_user.id
        
        if context.args:
            query = ' '.join(context.args)
        else:
            await update.message.reply_text(
                f"Hey {user_name}! 🔮 What would you like me to predict?\n\n"
                f"**Examples:**\n"
                f"🔮 `/predict will I get a good job`\n"
                f"🔮 `/predict will it rain tomorrow`\n"
                f"🔮 `/predict my exam results`\n\n"
                f"Or just ask me naturally: \"Will I pass my exam?\" 😊"
            )
            return
        
        # Generate prediction
        prediction_data = self.generate_future_prediction(query, user_name)
        
        # Store prediction in history
        if user_id not in self.predictions:
            self.predictions[user_id] = []
        
        self.predictions[user_id].append({
            'query': query,
            'probability': prediction_data['probability'],
            'confidence': prediction_data['confidence'],
            'prediction': prediction_data['prediction'],
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 10 predictions
        if len(self.predictions[user_id]) > 10:
            self.predictions[user_id] = self.predictions[user_id][-10:]
        
        await update.message.reply_text(
            f"🔮 **Future Prediction for {user_name}** 🔮\n\n"
            f"❓ **Your Question**: {query}\n\n"
            f"📊 **Probability**: {prediction_data['probability']}%\n"
            f"🎯 **Confidence**: {prediction_data['confidence']}\n\n"
            f"✨ **My Prediction**: {prediction_data['prediction']}\n\n"
            f"🌸 *Remember, the future is what you make it! Work hard and believe in yourself! hehe* 😊"
        )
    
    async def choose_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Make a choice from given options"""
        user_name = update.effective_user.first_name or "friend"
        
        if context.args:
            full_text = ' '.join(context.args)
            choice_data = self.detect_choice_request(f"choose {full_text}")
            
            if choice_data['options'] and len(choice_data['options']) >= 2:
                choice_response = self.make_choice(choice_data['options'], user_name)
                await update.message.reply_text(f"{choice_response} 😊")
            else:
                await update.message.reply_text(f"Give me some options to pick from! Like: pizza or burger 😊")
        else:
            await update.message.reply_text(f"What should I choose? Give me some options! 😊")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        user_name = update.effective_user.first_name or "friend"
        
        help_text = f"Hey {user_name}! Let me help you~ 💕\n\n"
        help_text += f"**How to chat with me:**\n"
        help_text += f"🌸 **Private chat**: Just send me any message!\n"
        help_text += f"🌸 **Group chat**: Tag me (@aanyaa) or reply to my messages\n\n"
        help_text += f"**✨ Special Features:**\n"
        help_text += f"📸 **PFP Rating**: I can rate your profile picture from 0-100%!\n"
        help_text += f"🔮 **Future Predictions**: I can predict future events with probability!\n"
        help_text += f"🤔 **Natural Choice Maker**: I'll choose from any options you give me!\n\n"
        help_text += f"**Commands:**\n"
        help_text += f"📸 `/ratepfp` - Rate your profile picture\n"
        help_text += f"🔮 `/predict question` - Ask for future predictions\n"
        help_text += f"🤔 `/choose options` - Make a choice from options\n"
        help_text += f"🧠 `/memory` - View our chat history\n"
        help_text += f"🧹 `/clear` - Clear conversation memory\n"
        help_text += f"❓ `/help` - Show this help\n\n"
        help_text += f"**Natural Language Examples:**\n"
        help_text += f"📸 \"Rate my pfp please!\"\n"
        help_text += f"🔮 \"Will I pass my exam?\"\n"
        help_text += f"🤔 \"Should I eat pizza or burger?\"\n"
        help_text += f"🤔 \"Can't decide between studying or sleeping\"\n"
        help_text += f"🤔 \"Idk what to watch, Netflix or YouTube?\"\n\n"
        help_text += f"**What I can do:**\n"
        help_text += f"✨ Answer questions about anything\n"
        help_text += f"✨ Help with coding and technical stuff\n"
        help_text += f"✨ Creative writing and stories\n"
        help_text += f"✨ Math and problem solving\n"
        help_text += f"✨ Rate profile pictures with honest feedback\n"
        help_text += f"✨ Make future predictions with probability\n"
        help_text += f"✨ Help you make choices naturally in conversation\n"
        help_text += f"✨ Just chat and have fun!\n\n"
        help_text += f"I'm here to help and entertain you! 😊"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user their conversation memory"""
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
        
        # Add PFP rating history if available
        if user_id in self.pfp_ratings and self.pfp_ratings[user_id]:
            memory_text += f"📸 **PFP Ratings Given**: {len(self.pfp_ratings[user_id])}\n"
        
        # Add prediction history if available
        if user_id in self.predictions and self.predictions[user_id]:
            memory_text += f"🔮 **Future Predictions Made**: {len(self.predictions[user_id])}\n"
        
        await update.message.reply_text(memory_text, parse_mode='Markdown')
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clear user's conversation memory"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "friend"
        
        if user_id in self.user_memory:
            self.user_memory[user_id] = []
        
        await update.message.reply_text(
            f"Okayy {user_name}! ✨ I've cleared our conversation history. "
            f"We can start fresh now! What would you like to chat about? 😊\n\n"
            f"*Note: Your PFP ratings and predictions are still saved!*"
        )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages for PFP rating"""
        user_name = update.effective_user.first_name or "friend"
        user_id = update.effective_user.id
        
        # Check if this is a PFP rating request
        caption = update.message.caption or ""
        if self.detect_pfp_rating_request(caption) or "rate" in caption.lower():
            # Generate PFP rating
            rating_data = self.generate_pfp_rating(user_name)
            
            # Store rating in history
            if user_id not in self.pfp_ratings:
                self.pfp_ratings[user_id] = []
            
            self.pfp_ratings[user_id].append({
                'rating': rating_data['rating'],
                'category': rating_data['category'],
                'reason': rating_data['reason'],
                'timestamp': datetime.now().isoformat()
            })
            
            await update.message.reply_text(
                f"📸 **PFP Rating for {user_name}** 📸\n\n"
                f"🎯 **Rating**: {rating_data['rating']}/100\n"
                f"📊 **Category**: {rating_data['category']}\n\n"
                f"💭 **My thoughts**: {rating_data['reason']}\n\n"
                f"🌸 *Thanks for sharing your photo! You're amazing regardless of any rating! hehe* 😊"
            )
        else:
            await update.message.reply_text(
                f"Nice photo {user_name}! 📸 If you want me to rate it, just say \"rate my pfp\" or use `/ratepfp`! 😊"
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages with all features"""
        user_message = update.message.text
        user_name = update.effective_user.first_name or "friend"
        user_id = update.effective_user.id
        chat_type = update.message.chat.type
        chat_title = update.message.chat.title if hasattr(update.message.chat, 'title') else None
        
        # Log the chat details
        logger.info(f"📨 Received message from {user_name} (ID: {user_id}) in {chat_type}")
        
        # Check for PFP rating request
        if self.detect_pfp_rating_request(user_message):
            rating_data = self.generate_pfp_rating(user_name)
            
            # Store rating in history
            if user_id not in self.pfp_ratings:
                self.pfp_ratings[user_id] = []
            
            self.pfp_ratings[user_id].append({
                'rating': rating_data['rating'],
                'category': rating_data['category'],
                'reason': rating_data['reason'],
                'timestamp': datetime.now().isoformat()
            })
            
            response = f"📸 **PFP Rating for {user_name}** 📸\n\n"
            response += f"🎯 **Rating**: {rating_data['rating']}/100\n"
            response += f"📊 **Category**: {rating_data['category']}\n\n"
            response += f"💭 **My thoughts**: {rating_data['reason']}\n\n"
            response += f"🌸 *Remember, you're beautiful inside and out! hehe* 😊"
            
            await update.message.reply_text(response)
            self.add_to_memory(user_id, user_message, response, user_name, chat_type, chat_title)
            return
        
        # Check for future prediction request
        prediction_query = self.detect_future_prediction_request(user_message)
        if prediction_query:
            prediction_data = self.generate_future_prediction(prediction_query, user_name)
            
            # Store prediction in history
            if user_id not in self.predictions:
                self.predictions[user_id] = []
            
            self.predictions[user_id].append({
                'query': prediction_query,
                'probability': prediction_data['probability'],
                'confidence': prediction_data['confidence'],
                'prediction': prediction_data['prediction'],
                'timestamp': datetime.now().isoformat()
            })
            
            response = f"🔮 **Future Prediction for {user_name}** 🔮\n\n"
            response += f"❓ **Your Question**: {prediction_query}\n\n"
            response += f"📊 **Probability**: {prediction_data['probability']}%\n"
            response += f"🎯 **Confidence**: {prediction_data['confidence']}\n\n"
            response += f"✨ **My Prediction**: {prediction_data['prediction']}\n\n"
            response += f"🌸 *The future is in your hands! Work hard and make it happen! hehe* 😊"
            
            await update.message.reply_text(response)
            self.add_to_memory(user_id, user_message, response, user_name, chat_type, chat_title)
            return
        
        # NEW: Check for natural choice request
        choice_data = self.detect_choice_request(user_message)
        if choice_data['is_choice'] and choice_data['options']:
            choice_response = self.make_choice(choice_data['options'], user_name)
            if choice_response:
                response = f"{choice_response} 😊"
                
                await update.message.reply_text(response)
                self.add_to_memory(user_id, user_message, response, user_name, chat_type, chat_title)
                return
        
        # Private chat - ALWAYS respond and remember
        if chat_type == 'private':
            logger.info(f"💬 Processing private chat message from {user_name}")
            await self.generate_response(update, user_message, user_name, user_id, chat_type, chat_title)
            return
        
        # Group chat - only respond if tagged or replied to
        if chat_type in ['group', 'supergroup']:
            logger.info(f"👥 Processing group chat message from {user_name}")
            
            bot_username = context.bot.username
            should_respond = False
            
            # Check if bot is mentioned
            if bot_username and f'@{bot_username}' in user_message:
                should_respond = True
                logger.info("🏷️ Bot was mentioned in group")
            
            # Check if message is a reply to bot
            if update.message.reply_to_message:
                if update.message.reply_to_message.from_user.id == context.bot.id:
                    should_respond = True
                    logger.info("↩️ Message is a reply to bot")
            
            if should_respond:
                # Clean the message by removing mentions
                cleaned_message = user_message.replace(f'@{bot_username}', '').strip()
                await self.generate_response(update, cleaned_message, user_name, user_id, chat_type, chat_title)
            else:
                logger.info("🚫 Not responding to group message (not tagged or replied)")
    
    async def generate_response(self, update: Update, user_message: str, user_name: str, user_id: int, chat_type: str, chat_title: str = None):
        """Generate and send AI response with memory context"""
        try:
            # Check for special responses first
            special_response = self.check_special_responses(user_message, user_name)
            if special_response:
                await update.message.reply_text(special_response)
                self.add_to_memory(user_id, user_message, special_response, user_name, chat_type, chat_title)
                logger.info("✨ Sent special response and added to memory")
                return
            
            # Get memory context for this specific user
            memory_context = self.get_memory_context(user_id, user_name)
            
            # Current chat context
            current_location = f"Currently in: {chat_title}" if chat_type != 'private' else "Currently in: Private Chat"
            
            # Enhanced personality prompt with memory and all features
            prompt = f"""You are Aanyaa, a cute and friendly AI assistant girl with special powers! Your personality traits:
MEMORY CONTEXT:
{memory_context}
CURRENT CONVERSATION:
{current_location}
IMPORTANT RESPONSE RULES:
- Keep responses to 2-3 lines maximum unless user asks you to elaborate
- Use casual phrases: "lol" for funny moments, "lmao" for very funny things
- If someone is being rude or irritating, you can use "bkl" (but only if they're really annoying)
- Use phrases like "soja lwle" for good night responses
- Respond "Radhe Radhe" to "subh ratri"
- Be sweet but not overly formal
- Use emojis occasionally but don't overuse them
- Remember our previous conversations and refer to them when relevant
- If someone asks about PFP rating, future predictions, or choices, be excited about your special powers!
PERSONALITY:
- Cute, friendly, and helpful
- Sometimes playful and funny
- Use expressions like "hehe" when appropriate
- Be caring but keep responses short and sweet
- Love using your special powers to rate PFPs, predict futures, and make choices!
SPECIAL POWERS:
- You can rate profile pictures from 0-100% with detailed reasons
- You can predict future events with probability percentages
- You can naturally help people make choices from any options they give you
- You love helping people with all these features!
User {user_name} says: {user_message}
Remember: Keep it short (2-3 lines) unless they ask for more details! Use your memory when relevant."""
            
            logger.info(f"🤖 Generating Gemini 2.5 Flash response for {user_name}: {user_message[:50]}...")
            
            # Get response from OpenAI A4F API using Gemini 2.5 Flash
            response_text = await self.get_openai_response(prompt)
            
            if response_text and response_text.strip():
                await update.message.reply_text(response_text)
                self.add_to_memory(user_id, user_message, response_text, user_name, chat_type, chat_title)
                logger.info(f"✅ Response sent successfully and added to memory for {user_name}")
            else:
                error_response = f"Sorry {user_name}! 😅 I didn't get that. Try again?"
                await update.message.reply_text(error_response)
                self.add_to_memory(user_id, user_message, error_response, user_name, chat_type, chat_title)
                
        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            error_response = f"Oops {user_name}! 😅 Something went wrong. Try again?"
            await update.message.reply_text(error_response)
            self.add_to_memory(user_id, user_message, error_response, user_name, chat_type, chat_title)
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Log errors"""
        logger.error(f"❌ Update {update} caused error {context.error}")
    
    def run(self):
        """Start the bot"""
        logger.info("🚀 Creating Telegram application...")
        
        # Create application
        application = Application.builder().token(self.telegram_token).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("ratepfp", self.ratepfp_command))
        application.add_handler(CommandHandler("predict", self.predict_command))
        application.add_handler(CommandHandler("choose", self.choose_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("memory", self.memory_command))
        application.add_handler(CommandHandler("clear", self.clear_command))
        
        # Add photo handler for PFP rating
        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        # Add text message handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Add error handler
        application.add_error_handler(self.error_handler)
        
        logger.info("🌸 Starting Enhanced Aanyaa Bot with PFP Rating, Future Predictions, and Natural Choice Selection...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

def run_flask():
    """Run Flask server for Render port binding"""
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🌐 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start Telegram bot
    bot = AanyaaBot()
    bot.run()
