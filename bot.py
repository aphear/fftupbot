import logging
import asyncio
import requests
import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import BufferedInputFile, WebAppInfo
from flask import Flask
from threading import Thread
from requests.exceptions import RequestException
from dotenv import load_dotenv

# ===== INITIALIZATION =====
load_dotenv()  # Load environment variables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)

# ===== CONFIGURATION =====
API_TOKEN = os.getenv('8074812211:AAHPqmH-xYcgB8Xot2nEG_sp5vYxHEoGGoA')
IMG_BB_API = os.getenv('c4b5c48ed3e11d9dac49d07c62b2b595')
ADMIN_ID = os.getenv('6042559774')
WEB_APP_URL = os.getenv('WEB_APP_URL', "https://aphear.rf.gd")

CHANNELS = [
    "@buysell470",
    "@freeearning470",
    "@freefiretournament420",
    "@dimondprove69",
    "@iconictraders69"
]

# Database configuration
DB_PATH = os.path.join(os.getcwd(), 'bot_data.db')

# ===== DATABASE FUNCTIONS =====
def init_db():
    """Initialize database with proper error handling"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users
                          (user_id INTEGER PRIMARY KEY, 
                           username TEXT,
                           first_name TEXT,
                           last_name TEXT,
                           join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        logging.info("Database initialized successfully")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

async def save_user(user_id: int, username: str, first_name: str, last_name: str):
    """Save user to database with error handling"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''INSERT OR IGNORE INTO users 
                          (user_id, username, first_name, last_name) 
                          VALUES (?, ?, ?, ?)''',
                       (user_id, username or '', first_name or '', last_name or ''))
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Error saving user {user_id}: {e}")
    finally:
        if conn:
            conn.close()

async def get_user_count():
    """Get total user count from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        return count
    except sqlite3.Error as e:
        logging.error(f"Error getting user count: {e}")
        return 0
    finally:
        if conn:
            conn.close()

# ===== BOT INITIALIZATION =====
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# ===== KEYBOARD BUILDERS =====
def channels_keyboard():
    builder = InlineKeyboardBuilder()
    for i, channel in enumerate(CHANNELS, 1):
        builder.button(text=f"Channel {i}", url=f"https://t.me/{channel[1:]}")
    builder.button(text="✅ JOINED", callback_data="check_channels")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def main_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🖼️ IMAGE TO URL")
    return builder.as_markup(resize_keyboard=True)

def web_app_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 OPEN WEB APP", web_app=WebAppInfo(url=WEB_APP_URL))
    return builder.as_markup()

def admin_panel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Broadcast Message", callback_data="broadcast_msg")
    builder.button(text="🎤 Broadcast Voice", callback_data="broadcast_voice")
    builder.button(text="🎥 Broadcast Video", callback_data="broadcast_video")
    builder.button(text="😀 Broadcast Sticker", callback_data="broadcast_sticker")
    builder.button(text="📊 User Stats", callback_data="user_stats")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

# ===== UTILITY FUNCTIONS =====
async def broadcast_message(message_type: str, content, caption=None):
    """Broadcast message to all users with error handling"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        
        success = 0
        for user in users:
            try:
                if message_type == "text":
                    await bot.send_message(user[0], content)
                elif message_type == "video":
                    await bot.send_video(user[0], video=content, caption=caption)
                elif message_type == "voice":
                    await bot.send_voice(user[0], voice=content, caption=caption)
                elif message_type == "sticker":
                    await bot.send_sticker(user[0], sticker=content)
                success += 1
            except Exception as e:
                logging.error(f"Failed to send to {user[0]}: {e}")
        return success
    except sqlite3.Error as e:
        logging.error(f"Database error during broadcast: {e}")
        return 0
    finally:
        if conn:
            conn.close()

def is_admin(user_id: int) -> bool:
    return str(user_id) == ADMIN_ID

async def check_user_joined(user_id: int):
    """Check if user joined all channels with error handling"""
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logging.error(f"Error checking channel {channel}: {e}")
            await bot.send_message(ADMIN_ID, f"⚠️ Channel check failed for {channel}: {e}")
            return False
    return True

# ===== MESSAGE HANDLERS =====
async def show_channel_requirement(message: types.Message):
    """Show channel join requirement"""
    try:
        await message.answer_photo(
            photo="https://i.ibb.co/Jjfq41fd/image.jpg",
            caption="<i>📌 নিচে দেওয়া সবগুলো চ্যানেলে জয়েন করে ( ✅ Joined ) বাটনে চাপ দিন ।</i>",
            reply_markup=channels_keyboard()
        )
    except Exception as e:
        logging.error(f"Error sending join requirement: {e}")
        await message.answer(
            "📌 নিচে দেওয়া সবগুলো চ্যানেলে জয়েন করে ( ✅ Joined ) বাটনে চাপ দিন ।",
            reply_markup=channels_keyboard()
        )

async def show_main_menu(message: types.Message):
    """Show main menu to user"""
    try:
        await message.answer_photo(
            photo="https://i.ibb.co/FLChhMvr/image.jpg",
            reply_markup=web_app_keyboard()
        )
        await message.answer(
            "( Image To Url ) ব্যবহার হবে ছবি থেকে Url বাহির করার জন্য :",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        logging.error(f"Error sending welcome message: {e}")
        await message.answer(
            "( Image To Url ) ব্যবহার হবে ছবি থেকে Url বাহির করার জন্য :",
            reply_markup=main_menu_keyboard()
        )

# ===== COMMAND HANDLERS =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start command"""
    await save_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    if await check_user_joined(message.from_user.id):
        await show_main_menu(message)
    else:
        await show_channel_requirement(message)

@dp.message(Command("adminpanel"))
async def admin_panel_command(message: types.Message):
    """Admin panel command handler"""
    if not is_admin(message.from_user.id):
        await message.reply("You Are Not An Admin ❌")
        return

    await message.answer(
        "👑 Admin Panel",
        reply_markup=admin_panel_keyboard()
    )

# ===== CALLBACK HANDLERS =====
@dp.callback_query(lambda c: c.data == "check_channels")
async def check_channels(callback: types.CallbackQuery):
    """Check if user joined all channels"""
    if await check_user_joined(callback.from_user.id):
        await callback.message.delete()
        await show_main_menu(callback.message)
    else:
        await callback.answer("❌ YOU MUST JOIN ALL CHANNELS FIRST!", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith('broadcast_'))
async def handle_broadcast_selection(callback: types.CallbackQuery):
    """Handle broadcast type selection"""
    if not is_admin(callback.from_user.id):
        await callback.answer("You Are Not An Admin ❌")
        return

    action = callback.data.split('_')[1]
    await callback.message.edit_text(
        f"Send the {action} you want to broadcast:",
        reply_markup=None
    )
    dp.broadcast_type = action

@dp.callback_query(lambda c: c.data == 'user_stats')
async def handle_user_stats(callback: types.CallbackQuery):
    """Show user statistics"""
    if not is_admin(callback.from_user.id):
        await callback.answer("You Are Not Admin ❌")
        return

    count = await get_user_count()
    await callback.message.edit_text(
        f"📊 Total Users: {count}",
        reply_markup=admin_panel_keyboard()
    )

# ===== CONTENT HANDLERS =====
@dp.message(lambda m: m.text == "🖼️ IMAGE TO URL")
async def request_image(message: types.Message):
    """Handle image to URL request"""
    try:
        await message.answer_photo(
            photo="https://i.ibb.co/Jjfq41fd/image.jpg",
            caption="📤 <b>( Image Url ) এর জন্য ছবি পাঠান:</b>\n\n"
                   "1. <b>📎 ক্লিপ আইকন এর উপর চাপ দিন</b> \n"
                   "2. <b>( ফটো ) সিলেক্ট করুন</b>\n"
                   "3. <b>ফটো সেন্ড করুন</b>\n\n"
                   "📌 <i>আপনি চাইলে একাধিক ছবি একসাথে পাঠাতে পারেন ।</i>"
        )
    except Exception as e:
        logging.error(f"Error sending instructions: {e}")
        await message.answer(
            "📤 <b>( Image Url ) এর জন্য ছবি পাঠান:</b>\n\n"
            "1. <b>📎 ক্লিপ আইকন এর উপর চাপ দিন</b> \n"
            "2. <b>( ফটো ) সিলেক্ট করুন</b>\n"
            "3. <b>ফটো সেন্ড করুন</b>\n\n"
            "📌 <i>আপনি চাইলে একাধিক ছবি একসাথে পাঠাতে পারেন ।</i>"
        )

@dp.message(lambda m: m.photo)
async def process_image(message: types.Message):
    """Process uploaded image"""
    processing_msg = None
    try:
        processing_msg = await message.reply("⏳ <b>PROCESSING YOUR IMAGE...</b>")

        file_id = message.photo[-1].file_id
        file = await bot.get_file(file_id)
        file_path = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"

        with requests.Session() as session:
            # Download image
            download_response = session.get(file_path, timeout=20)
            download_response.raise_for_status()
            image_data = download_response.content

            # Upload to ImgBB
            upload_response = session.post(
                "https://api.imgbb.com/1/upload",
                params={'key': IMG_BB_API},
                files={'image': ('image.jpg', image_data)},
                timeout=30
            )
            upload_response.raise_for_status()
            result = upload_response.json()
            image_url = result['data']['url']

        await processing_msg.edit_text("✅ <b>UPLOAD COMPLETE!</b>")
        await message.reply_photo(
            photo=BufferedInputFile(image_data, filename="result.jpg"),
            caption=f"🔗 This Is Your Image Url\n\n<code>{image_url}</code>\n\n<b>( উপরের লিংক এর উপর একটা ক্লিক করুন আপনার Image Url কপি হয়ে যাবে )</b>",
            reply_markup=main_menu_keyboard()
        )

    except RequestException as e:
        error_msg = f"Network error processing image: {e}"
        logging.error(error_msg)
        if processing_msg:
            await processing_msg.edit_text("❌ <b>NETWORK ERROR. PLEASE TRY AGAIN LATER</b>")
        else:
            await message.reply("❌ <b>NETWORK ERROR. PLEASE TRY AGAIN LATER</b>")
    except Exception as e:
        error_msg = f"Error processing image: {e}"
        logging.error(error_msg)
        if processing_msg:
            await processing_msg.edit_text("❌ <b>ERROR PROCESSING IMAGE</b>")
        else:
            await message.reply("❌ <b>ERROR PROCESSING IMAGE</b>")

@dp.message(lambda m: hasattr(dp, 'broadcast_type') and is_admin(m.from_user.id))
async def handle_broadcast_content(message: types.Message):
    """Handle broadcast content"""
    broadcast_type = dp.broadcast_type
    success = 0

    try:
        if broadcast_type == "msg":
            success = await broadcast_message("text", message.text)
        elif broadcast_type == "video":
            success = await broadcast_message("video", message.video.file_id, message.caption)
        elif broadcast_type == "voice":
            success = await broadcast_message("voice", message.voice.file_id, message.caption)
        elif broadcast_type == "sticker":
            success = await broadcast_message("sticker", message.sticker.file_id)

        await message.reply(f"✅ Broadcast sent to {success} users")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
    finally:
        if hasattr(dp, 'broadcast_type'):
            del dp.broadcast_type

# ===== ERROR HANDLER =====
@dp.errors()
async def error_handler(update: types.Update, exception: Exception):
    """Global error handler"""
    error_msg = f"⚠️ Exception occurred: {exception}\n\nUpdate: {update}"
    logging.error(error_msg)
    try:
        await bot.send_message(ADMIN_ID, error_msg[:4000])  # Truncate if too long
    except Exception as e:
        logging.error(f"Failed to send error notification: {e}")
    return True

# ===== FLASK KEEP-ALIVE =====
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health_check():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# ===== MAIN FUNCTION =====
async def main():
    # Initialize database
    init_db()
    
    # Start Flask server in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start the bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
