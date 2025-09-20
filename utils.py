import re
import asyncio
import yt_dlp
import ffmpeg
from shazamio import Shazam
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
import os

YOUTUBE_REGEX = r"(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+"
INSTAGRAM_REGEX = r"(https?://)?(www\.)?instagram\.com/(reel|p|tv)/[\w-]+"

user_usage = {}
USAGE_LIMIT = 10

async def detect_link(text):
    if re.search(YOUTUBE_REGEX, text):
        return 'youtube'
    if re.search(INSTAGRAM_REGEX, text):
        return 'instagram'
    return None

def get_video_id(url):
    match = re.search(r"(?:v=|youtu\.be/)([\w-]+)", url)
    return match.group(1) if match else None

async def download_media(url, media_type="video"):
    ydl_opts = {
        'outtmpl': f'temp_{media_type}.%(ext)s',
        'format': 'bestvideo+bestaudio/best' if media_type == 'video' else 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
    }
    if media_type == "audio":
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    loop = asyncio.get_event_loop()
    def run_ydl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if media_type == 'video':
                return ydl.prepare_filename(info)
            else:
                return f"temp_{media_type}.mp3"
    file_path = await loop.run_in_executor(None, run_ydl)
    return file_path

async def extract_audio(video_path, output_path="temp.mp3"):
    (
        ffmpeg
        .input(video_path)
        .output(output_path, format='mp3', acodec='libmp3lame')
        .overwrite_output()
        .run(quiet=True)
    )
    return output_path

async def recognize_music(file_path):
    shazam = Shazam()
    out = await shazam.recognize_song(file_path)
    if out['matches']:
        track = out['track']
        return {
            'title': track.get('title'),
            'subtitle': track.get('subtitle'),
            'url': track.get('url'),
        }
    return None

def check_usage(user_id):
    count = user_usage.get(user_id, 0)
    if count < USAGE_LIMIT:
        user_usage[user_id] = count + 1
        return True, USAGE_LIMIT - user_usage[user_id]
    return False, 0

def reset_usage(user_id):
    user_usage[user_id] = 0

async def check_channel_subscription(bot: Bot, user_id: int, channel_ids: list):
    if not channel_ids or not channel_ids[0]:  # No channels configured
        return True
    for channel_id in channel_ids:
        try:
            member = await bot.get_chat_member(chat_id=channel_id.strip(), user_id=user_id)
            if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                return False
        except Exception:
            # If we can't check the channel, assume user is not subscribed
            return False
    return True

def cleanup_temp_files():
    """Clean up temporary files"""
    temp_files = ['temp_video.mp4', 'temp_audio.mp3', 'temp.mp3', 'temp.mp4']
    for file in temp_files:
        if os.path.exists(file):
            try:
                os.remove(file)
            except Exception:
                pass 