import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from flask import Flask
import threading
import asyncio
from datetime import datetime
import json
import re
from typing import Dict, List

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
        
        # Enhanced memory system - stores last 10 chats per user
        self.user_memory = {}
        
        # Music system - stores playlists for each user
        self.user_playlists = {}
        
        # Currently playing songs in groups
        self.group_current_song = {}
        
        logger.info("✅ Bot initialized successfully with OpenAI A4F API and Enhanced Music System")
    
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
    
    # Enhanced Music System Methods
    def add_to_playlist(self, user_id: int, playlist_name: str, songs: List[str], user_name: str):
        """Add songs to user's playlist"""
        if user_id not in self.user_playlists:
            self.user_playlists[user_id] = {}
        
        if playlist_name not in self.user_playlists[user_id]:
            self.user_playlists[user_id][playlist_name] = {
                'songs': [],
                'created_date': datetime.now().isoformat(),
                'user_name': user_name
            }
        
        # Add new songs to existing playlist
        for song in songs:
            if song not in self.user_playlists[user_id][playlist_name]['songs']:
                self.user_playlists[user_id][playlist_name]['songs'].append(song)
        
        logger.info(f"Added {len(songs)} songs to playlist '{playlist_name}' for user {user_id}")
    
    def get_user_playlists(self, user_id: int) -> Dict:
        """Get all playlists for a user"""
        return self.user_playlists.get(user_id, {})
    
    def find_song_in_user_playlists(self, user_id: int, song_name: str) -> dict:
        """Find a song in user's playlists"""
        if user_id not in self.user_playlists:
            return None
        
        song_lower = song_name.lower()
        
        for playlist_name, playlist_data in self.user_playlists[user_id].items():
            for song in playlist_data['songs']:
                # Exact match or partial match
                if song_lower in song.lower() or song.lower() in song_lower:
                    return {
                        'song_name': song,
                        'playlist_name': playlist_name
                    }
        
        return None
    
    def detect_playlist_creation(self, message: str) -> Dict:
        """Detect if user is creating a playlist"""
        message_lower = message.lower()
        
        # Pattern for playlist creation
        playlist_patterns = [
            r'create playlist[:\s]*([^\n]+)',
            r'my ([a-zA-Z\s]+) playlist[:\s]*([^\n]+)',
            r'([a-zA-Z\s]+) mood songs[:\s]*([^\n]+)',
            r'playlist name[:\s]*([^\n]+)',
        ]
        
        for pattern in playlist_patterns:
            match = re.search(pattern, message_lower)
            if match:
                if len(match.groups()) == 2:
                    return {
                        'playlist_name': match.group(1).strip(),
                        'songs_text': match.group(2).strip()
                    }
                else:
                    return {
                        'playlist_name': match.group(1).strip(),
                        'songs_text': message[match.end():].strip()
                    }
        
        # Alternative patterns for mood-based playlists
        mood_patterns = [
            r'when i\'m (sad|happy|angry|excited|chill|romantic|energetic)[:\s]*([^\n]+)',
            r'for (workout|study|sleep|party|driving|relaxation)[:\s]*([^\n]+)',
        ]
        
        for pattern in mood_patterns:
            match = re.search(pattern, message_lower)
            if match:
                return {
                    'playlist_name': f"{match.group(1).title()} Mood",
                    'songs_text': match.group(2).strip()
                }
        
        return None
    
    def detect_playlist_request(self, message: str) -> str:
        """Detect if user wants to play their playlist"""
        message_lower = message.lower()
        
        # Common patterns for playlist requests
        patterns = [
            r'play my ([a-zA-Z\s]+) playlist',
            r'play ([a-zA-Z\s]+) playlist',
            r'start my ([a-zA-Z\s]+) songs',
            r'put on my ([a-zA-Z\s]+) music',
            r'i want to hear my ([a-zA-Z\s]+) playlist',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_songs_from_text(self, text: str) -> List[str]:
        """Extract song names from text"""
        # Split by common delimiters
        delimiters = ['\n', ',', ';', '|', '-', '•', '*']
        songs = [text]
        
        for delimiter in delimiters:
            temp = []
            for song in songs:
                temp.extend([s.strip() for s in song.split(delimiter) if s.strip()])
            songs = temp
        
        # Clean up song names
        cleaned_songs = []
        for song in songs:
            # Remove common prefixes/suffixes
            song = re.sub(r'^\d+[\.\)]\s*', '', song)  # Remove numbering
            song = re.sub(r'^[-•*]\s*', '', song)  # Remove bullet points
            song = song.strip()
            if song and len(song) > 2:  # Only keep meaningful song names
                cleaned_songs.append(song)
        
        return cleaned_songs
    
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
                    model="provider-6/gemini-2.5-flash",
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
        
        # Check if user has playlists
        playlist_info = ""
        if user_id in self.user_playlists and self.user_playlists[user_id]:
            playlist_count = len(self.user_playlists[user_id])
            playlist_info = f"\n🎵 You have {playlist_count} playlist{'s' if playlist_count > 1 else ''}!"
        
        chat_type_info = "private chat" if update.message.chat.type == 'private' else f"group ({update.message.chat.title})"
        
        await update.message.reply_text(
            f"Hi {user_name}! I'm Aanyaa 🌸\n"
            f"Your cute AI assistant with music powers!\n\n"
            f"💕 **Private chats**: Just message me!\n"
            f"💕 **Groups**: Tag me @{context.bot.username or 'aanyaa'} or reply\n"
            f"🧠 **Memory**: I remember our last 10 chats!\n"
            f"🎵 **Music**: Create playlists & play songs!\n\n"
            f"**Music Commands:**\n"
            f"🎶 `/play song_name` - Play song (searches your playlists)\n"
            f"🎵 `/playplaylist playlist_name` - Play entire playlist\n"
            f"📋 `/playlists` - View your playlists\n"
            f"🎼 `/mymusic` - Manage your music\n\n"
            f"**Other Commands:**\n"
            f"🧠 `/memory` - View chat history\n"
            f"🧹 `/clear` - Clear memory\n\n"
            f"**Natural Language:**\n"
            f"🎵 \"Play my happy playlist\" - Auto-plays playlist\n"
            f"📝 \"My chill playlist: song1, song2\" - Creates playlist\n\n"
            f"📍 **Current location**: {chat_type_info}{memory_info}{playlist_info}\n\n"
            f"What's up? 😊"
        )
    
    async def play_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced /play command that searches user playlists"""
        user_name = update.effective_user.first_name or "friend"
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Check if in group
        if update.message.chat.type == 'private':
            await update.message.reply_text(
                f"Hey {user_name}! 🎵 The /play command works in groups only!\n"
                f"Add me to a group and try `/play song_name` there! 😊"
            )
            return
        
        # Get song name from command
        if context.args:
            song_name = ' '.join(context.args).strip('"').strip("'")
        else:
            await update.message.reply_text(
                f"Hey {user_name}! 🎵 Please tell me what to play!\n"
                f"Use: `/play song_name` or `/play \"exact song name\"` 😊"
            )
            return
        
        # Search in user's playlists first
        found_song = self.find_song_in_user_playlists(user_id, song_name)
        
        if found_song:
            # Store currently playing song
            self.group_current_song[chat_id] = {
                'song': found_song['song_name'],
                'playlist': found_song['playlist_name'],
                'requested_by': user_name,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
            
            await update.message.reply_text(
                f"🎵 Now playing: **{found_song['song_name']}**\n"
                f"📀 From playlist: *{found_song['playlist_name']}*\n"
                f"🎤 Requested by: {user_name}\n"
                f"🎶 Playing from your personal collection! lol 😊"
            )
        else:
            # Play any song (not from playlist)
            self.group_current_song[chat_id] = {
                'song': song_name,
                'playlist': 'General',
                'requested_by': user_name,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
            
            await update.message.reply_text(
                f"🎵 Now playing: **{song_name}**\n"
                f"🎤 Requested by: {user_name}\n"
                f"🎶 Enjoy the music! 😊\n\n"
                f"💡 *Tip: Create playlists in our private chat for easier access!*"
            )
        
        logger.info(f"🎵 Playing song '{song_name}' in group {chat_id} requested by {user_name}")
    
    async def play_playlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Play entire playlists in groups"""
        user_name = update.effective_user.first_name or "friend"
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Check if in group
        if update.message.chat.type == 'private':
            await update.message.reply_text(
                f"Hey {user_name}! 🎵 Playlist playing works in groups only!\n"
                f"Use `/playplaylist playlist_name` in a group! 😊"
            )
            return
        
        # Get playlist name
        if context.args:
            playlist_name = ' '.join(context.args)
        else:
            # Show available playlists
            user_playlists = self.get_user_playlists(user_id)
            if user_playlists:
                playlist_list = "\n".join([f"🎵 {name}" for name in user_playlists.keys()])
                await update.message.reply_text(
                    f"Hey {user_name}! 🎵 Which playlist would you like to play?\n\n"
                    f"**Your playlists:**\n{playlist_list}\n\n"
                    f"Use: `/playplaylist playlist_name`"
                )
            else:
                await update.message.reply_text(
                    f"Hey {user_name}! You don't have any playlists yet! 😅\n"
                    f"Create some playlists in our private chat first! 🎵"
                )
            return
        
        # Find the playlist
        user_playlists = self.get_user_playlists(user_id)
        found_playlist = None
        
        for plist_name, plist_data in user_playlists.items():
            if playlist_name.lower() in plist_name.lower():
                found_playlist = {'name': plist_name, 'data': plist_data}
                break
        
        if not found_playlist:
            await update.message.reply_text(
                f"Hey {user_name}! I couldn't find playlist '{playlist_name}' 😅\n"
                f"Use `/playplaylist` to see your available playlists!"
            )
            return
        
        # Start playing playlist
        playlist_data = found_playlist['data']
        song_count = len(playlist_data['songs'])
        
        if song_count == 0:
            await update.message.reply_text(
                f"Hey {user_name}! Your '{found_playlist['name']}' playlist is empty! 😅\n"
                f"Add some songs to it first!"
            )
            return
        
        # Store playlist info
        self.group_current_song[chat_id] = {
            'song': playlist_data['songs'][0],
            'playlist': found_playlist['name'],
            'playlist_queue': playlist_data['songs'][1:],  # Remaining songs
            'current_song_index': 0,
            'requested_by': user_name,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }
        
        await update.message.reply_text(
            f"🎵 Now playing playlist: **{found_playlist['name']}**\n"
            f"🎶 Starting with: *{playlist_data['songs'][0]}*\n"
            f"📀 Total songs: {song_count}\n"
            f"🎤 Requested by: {user_name}\n\n"
            f"🎵 Enjoy your personal playlist! lol 😊"
        )
    
    async def playlists_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's playlists"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "friend"
        
        user_playlists = self.get_user_playlists(user_id)
        
        if not user_playlists:
            await update.message.reply_text(
                f"Hey {user_name}! 🎵 You don't have any playlists yet!\n\n"
                f"**How to create playlists:**\n"
                f"📝 Send me: \"My happy playlist: song1, song2, song3\"\n"
                f"📝 Or: \"Create playlist chill: song1, song2\"\n"
                f"📝 Or: \"When I'm sad: song1, song2\"\n\n"
                f"I'll remember all your playlists! 😊"
            )
            return
        
        playlist_text = f"🎵 **{user_name}'s Music Collection** 🎵\n\n"
        
        for playlist_name, playlist_data in user_playlists.items():
            song_count = len(playlist_data['songs'])
            playlist_text += f"📀 **{playlist_name}**\n"
            playlist_text += f"   🎶 {song_count} song{'s' if song_count != 1 else ''}\n"
            
            # Show first 3 songs
            for i, song in enumerate(playlist_data['songs'][:3]):
                playlist_text += f"   • {song}\n"
            
            if song_count > 3:
                playlist_text += f"   ... and {song_count - 3} more!\n"
            
            playlist_text += "\n"
        
        playlist_text += f"💡 **Tip**: Use `/play song_name` in groups to play music!\n"
        playlist_text += f"🎵 **Or**: Use `/playplaylist playlist_name` to play entire playlists!"
        
        await update.message.reply_text(playlist_text, parse_mode='Markdown')
    
    async def mymusic_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manage user's music"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "friend"
        
        if update.message.chat.type != 'private':
            await update.message.reply_text(
                f"Hey {user_name}! 🎵 Use `/mymusic` in our private chat for playlist management! 😊"
            )
            return
        
        user_playlists = self.get_user_playlists(user_id)
        
        music_text = f"🎵 **Music Management for {user_name}** 🎵\n\n"
        
        if user_playlists:
            music_text += f"**Your Playlists ({len(user_playlists)}):**\n"
            for playlist_name, playlist_data in user_playlists.items():
                music_text += f"📀 {playlist_name} ({len(playlist_data['songs'])} songs)\n"
        else:
            music_text += "**No playlists yet!**\n"
        
        music_text += f"\n**How to create playlists:**\n"
        music_text += f"📝 \"My happy playlist: song1, song2, song3\"\n"
        music_text += f"📝 \"Create playlist chill: song1, song2\"\n"
        music_text += f"📝 \"When I'm sad: song1, song2\"\n"
        music_text += f"📝 \"For workout: song1, song2\"\n\n"
        
        music_text += f"**How to play in groups:**\n"
        music_text += f"🎶 `/play song_name` - Play specific song\n"
        music_text += f"🎵 `/playplaylist playlist_name` - Play entire playlist\n"
        music_text += f"🗣️ \"Play my happy playlist\" - Natural language request\n\n"
        
        music_text += f"**Tips:**\n"
        music_text += f"🎶 I can handle multiple playlists per mood!\n"
        music_text += f"🎵 Songs from your playlists get priority in `/play`!\n"
        music_text += f"📋 Use `/playlists` to view all your playlists!\n\n"
        
        music_text += f"Just tell me about your music preferences! 😊"
        
        await update.message.reply_text(music_text, parse_mode='Markdown')
    
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
            f"*Note: Your playlists are still saved! Use `/playlists` to view them.*"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced message handler with playlist request detection"""
        user_message = update.message.text
        user_name = update.effective_user.first_name or "friend"
        user_id = update.effective_user.id
        chat_type = update.message.chat.type
        chat_title = update.message.chat.title if hasattr(update.message.chat, 'title') else None
        
        # Log the chat details
        logger.info(f"📨 Received message from {user_name} (ID: {user_id}) in {chat_type}")
        
        # Check for playlist creation in private chat
        if chat_type == 'private':
            playlist_data = self.detect_playlist_creation(user_message)
            if playlist_data:
                songs = self.extract_songs_from_text(playlist_data['songs_text'])
                if songs:
                    self.add_to_playlist(user_id, playlist_data['playlist_name'], songs, user_name)
                    response = f"🎵 Awesome! I've created your **{playlist_data['playlist_name']}** playlist with {len(songs)} songs! 😊\n\n"
                    response += f"**Songs added:**\n"
                    for i, song in enumerate(songs[:5], 1):
                        response += f"{i}. {song}\n"
                    if len(songs) > 5:
                        response += f"... and {len(songs) - 5} more!\n"
                    response += f"\n**How to play:**\n"
                    response += f"🎵 `/playplaylist {playlist_data['playlist_name']}` - Play entire playlist\n"
                    response += f"🎶 `/play song_name` - Play specific song\n"
                    response += f"🗣️ \"Play my {playlist_data['playlist_name'].lower()} playlist\" - Natural language\n\n"
                    response += f"Use `/playlists` to view all your playlists! 🎶"
                    
                    await update.message.reply_text(response, parse_mode='Markdown')
                    self.add_to_memory(user_id, user_message, response, user_name, chat_type, chat_title)
                    return
        
        # Check for playlist requests in groups
        if chat_type in ['group', 'supergroup']:
            playlist_request = self.detect_playlist_request(user_message)
            if playlist_request:
                # Check if user has this playlist
                user_playlists = self.get_user_playlists(user_id)
                found_playlist = None
                
                for plist_name, plist_data in user_playlists.items():
                    if playlist_request.lower() in plist_name.lower():
                        found_playlist = {'name': plist_name, 'data': plist_data}
                        break
                
                if found_playlist:
                    # Auto-play the playlist
                    chat_id = update.effective_chat.id
                    playlist_data = found_playlist['data']
                    
                    if playlist_data['songs']:
                        self.group_current_song[chat_id] = {
                            'song': playlist_data['songs'][0],
                            'playlist': found_playlist['name'],
                            'playlist_queue': playlist_data['songs'][1:],
                            'current_song_index': 0,
                            'requested_by': user_name,
                            'user_id': user_id,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        response = f"🎵 Playing your **{found_playlist['name']}** playlist! 😊\n"
                        response += f"🎶 Starting with: *{playlist_data['songs'][0]}*\n"
                        response += f"📀 {len(playlist_data['songs'])} songs in queue\n"
                        response += f"🎵 Enjoy your music! lol"
                        
                        await update.message.reply_text(response, parse_mode='Markdown')
                        self.add_to_memory(user_id, user_message, response, user_name, chat_type, chat_title)
                        return
                else:
                    response = f"Hey {user_name}! I couldn't find your '{playlist_request}' playlist 😅\n"
                    response += f"Create it in our private chat first! 🎵"
                    
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
        """Generate and send AI response with memory and music context"""
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
            
            # Get user's playlist context
            playlist_context = ""
            if user_id in self.user_playlists and self.user_playlists[user_id]:
                playlist_names = list(self.user_playlists[user_id].keys())
                playlist_context = f"User's playlists: {', '.join(playlist_names)}"
            
            # Current chat context
            current_location = f"Currently in: {chat_title}" if chat_type != 'private' else "Currently in: Private Chat"
            
            # Enhanced personality prompt with memory and music context
            prompt = f"""You are Aanyaa, a cute and friendly AI assistant girl with music powers! Your personality traits:

MEMORY CONTEXT:
{memory_context}

MUSIC CONTEXT:
{playlist_context}

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
- If someone talks about music, be excited and suggest they create playlists!

PERSONALITY:
- Cute, friendly, and helpful
- Sometimes playful and funny
- Use expressions like "hehe" when appropriate
- Be caring but keep responses short and sweet
- Love music and helping with playlists!

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
        application.add_handler(CommandHandler("play", self.play_command))
        application.add_handler(CommandHandler("playplaylist", self.play_playlist_command))
        application.add_handler(CommandHandler("playlists", self.playlists_command))
        application.add_handler(CommandHandler("mymusic", self.mymusic_command))
        application.add_handler(CommandHandler("memory", self.memory_command))
        application.add_handler(CommandHandler("clear", self.clear_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Add error handler
        application.add_error_handler(self.error_handler)
        
        logger.info("🎵 Starting enhanced Aanyaa bot with complete music system and AI personality...")
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
