import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from utils import detect_link, download_media, recognize_music, check_usage, check_channel_subscription, cleanup_temp_files, USAGE_LIMIT

from dotenv import load_dotenv
import os


# .env fayldan o‘qish
load_dotenv()

# 1️⃣ Agar .env faylda yozilgan bo‘lsa shu o‘qiladi
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 2️⃣ Agar .env ishlamasa, to‘g‘ridan-to‘g‘ri qo‘lda token qo‘yishingiz mumkin
if not BOT_TOKEN:
    BOT_TOKEN = "7538554079:AAECSuTDUf3Lc-tkyHlplvvR6UEFlxIZuxY"

CHANNEL_IDS = os.getenv("CHANNEL_IDS", "").split(",") if os.getenv("CHANNEL_IDS") else []

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DOWNLOAD_VIDEO = "download_video"
DOWNLOAD_AUDIO = "download_audio"

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    welcome_text = """👋 Welcome to the Video/Audio Downloader Bot!

🎯 **What I can do:**
• Download videos from YouTube and Instagram
• Extract audio from videos
• Recognize music in downloaded content
• Support for reels, posts, and regular videos

📊 **Usage:**
• Free downloads: 10 per user
• After limit: Join our channels for unlimited access

🚀 **How to use:**
Just send me a YouTube or Instagram link and choose your preferred format!

Need help? Use /help command."""
    await message.answer(welcome_text)

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    help_text = """❓ **Help & Instructions**

🔗 **Supported Links:**
• YouTube: youtube.com/watch?v=... or youtu.be/...
• Instagram: instagram.com/reel/... or instagram.com/p/...

📱 **How to use:**
1. Send me a supported link
2. Choose "Download Video" or "Download Audio"
3. Wait for the download to complete

🎵 **Music Recognition:**
The bot automatically tries to identify music in downloaded content using Shazam technology.

📊 **Usage Limits:**
• Free users: 10 downloads
• Channel subscribers: Unlimited downloads

🆘 **Need Support?**
Contact the bot administrator if you encounter any issues."""
    await message.answer(help_text)

@dp.message()
async def link_handler(message: types.Message):
    link_type = await detect_link(message.text)
    if not link_type:
        return
    
    user_id = message.from_user.id
    allowed, left = check_usage(user_id)
    
    if not allowed:
        # Check channel subscription
        is_subscribed = await check_channel_subscription(bot, user_id, CHANNEL_IDS)
        if not is_subscribed:
            join_links = "\n".join([f"@{cid.lstrip('@')}" for cid in CHANNEL_IDS if cid.strip()])
            await message.answer(f"⚠️ You've reached the free usage limit ({USAGE_LIMIT} downloads).\n\nPlease join our channels to continue:\n{join_links}")
            return
    
    # Show usage info
    usage_text = f"📊 Free downloads remaining: {left}/{USAGE_LIMIT}"
    if link_type == 'youtube':
        usage_text += "\n🎥 YouTube link detected"
    elif link_type == 'instagram':
        usage_text += "\n📸 Instagram link detected"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 Download Video", callback_data=f"{DOWNLOAD_VIDEO}|{message.text}"),
         InlineKeyboardButton(text="🎵 Download Audio", callback_data=f"{DOWNLOAD_AUDIO}|{message.text}")]
    ])
    await message.answer(f"{usage_text}\n\nChoose download type:", reply_markup=kb)

@dp.callback_query(F.data.startswith(DOWNLOAD_VIDEO))
async def video_callback(call: types.CallbackQuery):
    try:
        await call.answer()  # Acknowledge the callback
        _, url = call.data.split("|", 1)
        user_id = call.from_user.id
        allowed, left = check_usage(user_id)
        if not allowed:
            is_subscribed = await check_channel_subscription(bot, user_id, CHANNEL_IDS)
            if not is_subscribed:
                join_links = "\n".join([f"@{cid.lstrip('@')}" for cid in CHANNEL_IDS if cid.strip()])
                await call.message.answer(f"⚠️ You've reached the free usage limit ({USAGE_LIMIT} downloads).\n\nPlease join our channels to continue:\n{join_links}")
                return
        
        msg = await call.message.answer("📥 Downloading video, please wait...")
        file_path = None
        try:
            file_path = await download_media(url, media_type="video")
            if not os.path.exists(file_path):
                raise Exception("Download failed - file not found")
            
            # Send video with caption showing remaining usage
            caption = f"✅ Video downloaded successfully!\nRemaining free downloads: {left}"
            await bot.send_video(call.from_user.id, types.FSInputFile(file_path), caption=caption)
            
            # Try music recognition
            try:
                music_info = await recognize_music(file_path)
                if music_info:
                    await call.message.answer(f"🎵 Recognized track: {music_info['title']} - {music_info['subtitle']}\n🔗 Listen: {music_info['url']}")
            except Exception:
                pass  # Music recognition is optional
            
        except Exception as e:
            await call.message.answer(f"❌ Error downloading video: {str(e)}")
        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            await msg.delete()
            
    except Exception as e:
        await call.message.answer(f"❌ An error occurred: {str(e)}")

@dp.callback_query(F.data.startswith(DOWNLOAD_AUDIO))
async def audio_callback(call: types.CallbackQuery):
    try:
        await call.answer()  # Acknowledge the callback
        _, url = call.data.split("|", 1)
        user_id = call.from_user.id
        allowed, left = check_usage(user_id)
        if not allowed:
            is_subscribed = await check_channel_subscription(bot, user_id, CHANNEL_IDS)
            if not is_subscribed:
                join_links = "\n".join([f"@{cid.lstrip('@')}" for cid in CHANNEL_IDS if cid.strip()])
                await call.message.answer(f"⚠️ You've reached the free usage limit ({USAGE_LIMIT} downloads).\n\nPlease join our channels to continue:\n{join_links}")
                return
        
        msg = await call.message.answer("🎵 Extracting audio, please wait...")
        file_path = None
        try:
            file_path = await download_media(url, media_type="audio")
            if not os.path.exists(file_path):
                raise Exception("Download failed - file not found")
            
            # Send audio with caption showing remaining usage
            caption = f"✅ Audio extracted successfully!\nRemaining free downloads: {left}"
            await bot.send_audio(call.from_user.id, types.FSInputFile(file_path), caption=caption)
            
            # Try music recognition
            try:
                music_info = await recognize_music(file_path)
                if music_info:
                    await call.message.answer(f"🎵 Recognized track: {music_info['title']} - {music_info['subtitle']}\n🔗 Listen: {music_info['url']}")
            except Exception:
                pass  # Music recognition is optional
            
        except Exception as e:
            await call.message.answer(f"❌ Error extracting audio: {str(e)}")
        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            await msg.delete()
            
    except Exception as e:
        await call.message.answer(f"❌ An error occurred: {str(e)}")

async def main():
    # Clean up any leftover temp files on startup
    cleanup_temp_files()
    
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting bot...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        cleanup_temp_files()

if __name__ == "__main__":
    asyncio.run(main()) 