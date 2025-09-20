import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from dotenv import load_dotenv
from utils import (
    detect_link, download_media, recognize_music,
    check_usage, check_channel_subscription,
    cleanup_temp_files, USAGE_LIMIT
)

# .env fayldan o‘qish
load_dotenv()

BOT_TOKEN = os.getenv("7538554079:AAECSuTDUf3Lc-tkyHlplvvR6UEFlxIZuxY")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

CHANNEL_IDS = os.getenv("CHANNEL_IDS", "").split(",") if os.getenv("CHANNEL_IDS") else []

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DOWNLOAD_VIDEO = "download_video"
DOWNLOAD_AUDIO = "download_audio"

# oddiy dictionary foydalanuvchi linklarini saqlash uchun
user_links = {}

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
Just send me a YouTube or Instagram link and choose your preferred format!"""
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
The bot automatically tries to identify music in downloaded content.

📊 **Usage Limits:**
• Free users: 10 downloads
• Channel subscribers: Unlimited downloads"""
    await message.answer(help_text)

@dp.message()
async def link_handler(message: types.Message):
    link_type = await detect_link(message.text)
    if not link_type:
        return
    
    user_id = message.from_user.id
    allowed, left = check_usage(user_id)
    
    if not allowed:
        is_subscribed = await check_channel_subscription(bot, user_id, CHANNEL_IDS)
        if not is_subscribed:
            join_links = "\n".join([f"@{cid.lstrip('@')}" for cid in CHANNEL_IDS if cid.strip()])
            await message.answer(
                f"⚠️ You've reached the free usage limit ({USAGE_LIMIT} downloads).\n\n"
                f"Please join our channels to continue:\n{join_links}"
            )
            return
    
    user_links[user_id] = message.text
    usage_text = f"📊 Free downloads remaining: {left}/{USAGE_LIMIT}"
    if link_type == 'youtube':
        usage_text += "\n🎥 YouTube link detected"
    elif link_type == 'instagram':
        usage_text += "\n📸 Instagram link detected"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎥 Download Video", callback_data=DOWNLOAD_VIDEO),
            InlineKeyboardButton(text="🎵 Download Audio", callback_data=DOWNLOAD_AUDIO)
        ]
    ])
    await message.answer(f"{usage_text}\n\nChoose download type:", reply_markup=kb)

@dp.callback_query(F.data == DOWNLOAD_VIDEO)
async def video_callback(call: types.CallbackQuery):
    try:
        await call.answer()
        user_id = call.from_user.id
        url = user_links.get(user_id)
        if not url:
            await call.message.answer("❌ Link topilmadi. Iltimos, qayta yuboring.")
            return

        allowed, left = check_usage(user_id)
        if not allowed:
            is_subscribed = await check_channel_subscription(bot, user_id, CHANNEL_IDS)
            if not is_subscribed:
                join_links = "\n".join([f"@{cid.lstrip('@')}" for cid in CHANNEL_IDS if cid.strip()])
                await call.message.answer(
                    f"⚠️ You've reached the free usage limit ({USAGE_LIMIT} downloads).\n\n"
                    f"Please join our channels to continue:\n{join_links}"
                )
                return
        
        msg = await call.message.answer("📥 Downloading video, please wait...")
        file_path = None
        try:
            file_path = await download_media(url, media_type="video")
            if not os.path.exists(file_path):
                raise Exception("Download failed - file not found")
            
            caption = f"✅ Video downloaded successfully!\nRemaining free downloads: {left}"
            await bot.send_video(chat_id=user_id, video=types.FSInputFile(file_path), caption=caption)
            
            try:
                music_info = await recognize_music(file_path)
                if music_info:
                    await call.message.answer(
                        f"🎵 Recognized track: {music_info['title']} - {music_info['subtitle']}\n"
                        f"🔗 Listen: {music_info['url']}"
                    )
            except Exception:
                pass
        except Exception as e:
            await call.message.answer(f"❌ Error downloading video: {str(e)}")
        finally:
            if file_path and os.path.exists(file_path):
                try: os.remove(file_path)
                except Exception: pass
            await msg.delete()
    except Exception as e:
        await call.message.answer(f"❌ An error occurred: {str(e)}")

@dp.callback_query(F.data == DOWNLOAD_AUDIO)
async def audio_callback(call: types.CallbackQuery):
    try:
        await call.answer()
        user_id = call.from_user.id
        url = user_links.get(user_id)
        if not url:
            await call.message.answer("❌ Link topilmadi. Iltimos, qayta yuboring.")
            return

        allowed, left = check_usage(user_id)
        if not allowed:
            is_subscribed = await check_channel_subscription(bot, user_id, CHANNEL_IDS)
            if not is_subscribed:
                join_links = "\n".join([f"@{cid.lstrip('@')}" for cid in CHANNEL_IDS if cid.strip()])
                await call.message.answer(
                    f"⚠️ You've reached the free usage limit ({USAGE_LIMIT} downloads).\n\n"
                    f"Please join our channels to continue:\n{join_links}"
                )
                return
        
        msg = await call.message.answer("🎵 Extracting audio, please wait...")
        file_path = None
        try:
            file_path = await download_media(url, media_type="audio")
            if not os.path.exists(file_path):
                raise Exception("Download failed - file not found")
            
            caption = f"✅ Audio extracted successfully!\nRemaining free downloads: {left}"
            await bot.send_audio(chat_id=user_id, audio=types.FSInputFile(file_path), caption=caption)
            
            try:
                music_info = await recognize_music(file_path)
                if music_info:
                    await call.message.answer(
                        f"🎵 Recognized track: {music_info['title']} - {music_info['subtitle']}\n"
                        f"🔗 Listen: {music_info['url']}"
                    )
            except Exception:
                pass
        except Exception as e:
            await call.message.answer(f"❌ Error extracting audio: {str(e)}")
        finally:
            if file_path and os.path.exists(file_path):
                try: os.remove(file_path)
                except Exception: pass
            await msg.delete()
    except Exception as e:
        await call.message.answer(f"❌ An error occurred: {str(e)}")

async def main():
    cleanup_temp_files()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    try:
        await dp.start_polling(bot)
    finally:
        cleanup_temp_files()

if __name__ == "__main__":
    asyncio.run(main())
