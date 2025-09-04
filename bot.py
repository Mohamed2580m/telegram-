import telebot
from telebot import types
import yt_dlp
import os
import re
import time
import threading
from datetime import datetime
import requests
from dotenv import load_dotenv  # ✅ لتحميل التوكن من .env
from flask import Flask  # ✅ تم إضافة هذا السطر
import threading  # ✅ تم إضافة هذا السطر

# --------------------------
# تحميل المتغيرات من ملف .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ التوكن غير موجود! تأكدي إنك ضيفاه في ملف .env")

bot = telebot.TeleBot(BOT_TOKEN)
# --------------------------

# --------------------------
# دالة لتحويل روابط Facebook share/r إلى الرابط النهائي
def resolve_facebook_link(url):
    if "facebook.com/share/r/" in url:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, allow_redirects=True, headers=headers, timeout=10)
            final_url = response.url
            if "facebook.com" in final_url and "/share/r/" not in final_url:
                return final_url
            else:
                return url
        except Exception as e:
            print("خطأ أثناء محاولة تحويل الرابط:", e)
            return url
    return url
# --------------------------

# رسالة الترحيب
WELCOME_MESSAGE = """
🚀 ✦ 𝐁𝐨𝐝𝐲 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐫 ✦ — بوت الوسائط الأسطوري
━━━━━━━━━━━━━━━━━━━━

🎥 ❖ حمّل أي فيديو
من YouTube | TikTok | Facebook | Instagram | Twitter

🎵 ❖ حوّل الفيديو لصوت MP3
بسهولة وسرعة

💎 ❖ سريع ومجاني
استلم الملفات جوه التليجرام مباشرة

🌍 ❖ سهل الاستخدام
ابعت الرابط → اختار الصيغة → استلم ملفك

━━━━━━━━━━━━━━━━━━━━
🔥 ✦ استمتع بتنزيلات أسطورية مع Body Downloader! ✦
"""

# تعريف المنصات المدعومة
SUPPORTED_PLATFORMS = {
    'youtube': {
        'patterns': [r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+'],
        'name': 'YouTube'
    },
    'tiktok': {
        'patterns': [r'(https?://)?(www\.)?(tiktok\.com|vt\.tiktok\.com)/.+'],
        'name': 'TikTok'
    },
    'facebook': {
        'patterns': [r'(https?://)?(www\.)?(facebook\.com|fb\.watch)/.+'],
        'name': 'Facebook'
    },
    'instagram': {
        'patterns': [r'(https?://)?(www\.)?(instagram\.com)/.+'],
        'name': 'Instagram'
    },
    'twitter': {
        'patterns': [r'(https?://)?(www\.)?(twitter\.com|x\.com)/.+'],
        'name': 'Twitter'
    }
}

# قاموس لتخزين حالة التحميل لكل مستخدم
download_status = {}

# --------------------------
# أمر start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, WELCOME_MESSAGE)

# --------------------------
# التحقق من الروابط المدعومة
def is_supported_url(url):
    resolved_url = resolve_facebook_link(url)
    for platform, data in SUPPORTED_PLATFORMS.items():
        for pattern in data['patterns']:
            if re.match(pattern, resolved_url):
                return True, data['name']
    return False, None

# --------------------------
# دالة لإنشاء شريط التقدم
def create_progress_bar(percentage, length=10):
    filled_length = int(length * percentage // 100)
    bar = '█' * filled_length + '░' * (length - filled_length)
    return f"[{bar}] {percentage:.1f}%"

# --------------------------
# دالة لتحديث حالة التحميل
def update_progress(d, chat_id, message_id, url, start_time):
    if d['status'] == 'downloading':
        speed = d.get('speed', 0)
        total_bytes = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
        downloaded_bytes = d.get('downloaded_bytes', 0)

        if total_bytes > 0 and downloaded_bytes > 0 and speed > 0:
            percentage = min(100, downloaded_bytes * 100 / total_bytes)
            remaining_bytes = total_bytes - downloaded_bytes
            eta = remaining_bytes / speed if speed > 0 else 0

            download_status[chat_id] = {
                'percentage': percentage,
                'speed': speed,
                'eta': eta,
                'total_size': total_bytes
            }

            current_time = time.time()
            last_update = download_status[chat_id].get('last_update', 0)

            if current_time - last_update >= 2 or abs(percentage - download_status[chat_id].get('last_percentage', 0)) >= 5:
                progress_bar = create_progress_bar(percentage)
                speed_str = format_size(speed) + "/s"
                total_size_str = format_size(total_bytes)
                downloaded_size_str = format_size(downloaded_bytes)
                eta_str = format_time(eta) if eta > 0 else "جاري التقدير..."

                progress_message = f"""
⏳ جاري التحميل...

{progress_bar}

📊 التقدم: {downloaded_size_str} / {total_size_str}
🚀 السرعة: {speed_str}
⏱ الوقت المتبقي: {eta_str}

يتم التحديث تلقائياً...
"""
                try:
                    bot.edit_message_text(
                        progress_message,
                        chat_id,
                        message_id,
                        parse_mode='Markdown'
                    )
                    download_status[chat_id]['last_update'] = current_time
                    download_status[chat_id]['last_percentage'] = percentage
                except:
                    pass

# --------------------------
def format_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

# --------------------------
def format_time(seconds):
    if seconds < 60:
        return f"{int(seconds)} ثانية"
    elif seconds < 3600:
        return f"{int(seconds // 60)} دقيقة {int(seconds % 60)} ثانية"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours} ساعة {minutes} دقيقة"

# --------------------------
@bot.message_handler(func=lambda message: True)
def handle_link(message):
    url = message.text.strip()
    if not url.startswith(('http://', 'https://')):
        bot.send_message(message.chat.id, "❌ يرجى إرسال رابط صالح للتحميل.")
        return
    resolved_url = resolve_facebook_link(url)
    supported, platform_name = is_supported_url(resolved_url)
    if not supported:
        bot.send_message(message.chat.id, "❌ الرابط غير مدعوم! استخدم YouTube, TikTok, Facebook, Instagram, أو Twitter.")
        return
    bot.send_message(message.chat.id, f"✅ تم التعرف على الرابط من {platform_name}")
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('🎬 فيديو MP4', '🎵 صوت MP3')
    msg = bot.send_message(message.chat.id, "اختر صيغة التحميل:", reply_markup=markup)
    bot.register_next_step_handler(msg, lambda m: process_download_choice(m, resolved_url))

# --------------------------
def process_download_choice(message, url):
    choice = message.text
    chat_id = message.chat.id
    if choice not in ['🎬 فيديو MP4', '🎵 صوت MP3']:
        bot.send_message(chat_id, "❌ اختيار غير صالح. يرجى استخدام الأزرار المقدمة.")
        return
    wait_msg = bot.send_message(chat_id, "⏳ جاري التحضير للتحميل...")
    download_media(chat_id, url, choice, wait_msg.message_id)

# --------------------------
def download_media(chat_id, url, choice, message_id):
    download_status[chat_id] = {
        'percentage': 0, 'speed': 0, 'eta': 0,
        'total_size': 0, 'last_update': 0, 'last_percentage': 0
    }
    options = {
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True, 'no_warnings': True,

        'progress_hooks': [lambda d: update_progress(d, chat_id, message_id, url, time.time())],
    }
    if choice == '🎵 صوت MP3':
        options.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        options.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })
    try:
        os.makedirs('downloads', exist_ok=True)
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            file_size = info.get('filesize') or info.get('filesize_estimate', 0)
            if file_size > 1000 * 1024 * 1024:
                bot.edit_message_text("❌ حجم الملف يتجاوز 1GB وهو أكبر من الحد المسموح به.", chat_id, message_id)
                return
            bot.edit_message_text("⏳ جاري التحضير للتحميل، يرجى الانتظار...", chat_id, message_id)

            def download_thread():
                try:
                    ydl.download([url])
                    filename = ydl.prepare_filename(info)
                    if choice == '🎵 صوت MP3':
                        filename = os.path.splitext(filename)[0] + '.mp3'
                    if not os.path.exists(filename):
                        bot.edit_message_text("❌ فشل في تحميل الملف.", chat_id, message_id)
                        return
                    file_size = os.path.getsize(filename)
                    if file_size > 1000 * 1024 * 1024:
                        bot.edit_message_text("❌ حجم الملف النهائي يتجاوز 1GB وهو أكبر من الحد المسموح به.", chat_id, message_id)
                        os.remove(filename)
                        return
                    bot.edit_message_text("✅ تم التحميل بنجاح! جاري الإرسال...", chat_id, message_id)
                    if choice == '🎵 صوت MP3':
                        with open(filename, 'rb') as audio_file:
                            bot.send_audio(chat_id, audio_file, timeout=300)
                    else:
                        with open(filename, 'rb') as video_file:
                            bot.send_video(chat_id, video_file, timeout=300, supports_streaming=True)
                    os.remove(filename)
                    bot.delete_message(chat_id, message_id)
                except Exception as e:
                    bot.edit_message_text(f"❌ حدث خطأ أثناء التحميل: {str(e)}", chat_id, message_id)
            thread = threading.Thread(target=download_thread)
            thread.start()
    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ غير متوقع: {str(e)}", chat_id, message_id)

# --------------------------
# ✅ هذا الجزء هو الذي تم إضافته ليحل محل bot.infinity_polling()
# لتشغيل البوت بشكل دائم مع خادم الويب
app = Flask(_name_)

def run_bot():
    print("Body Downloader Bot is running...")
    bot.infinity_polling()

@app.route('/')
def home():
    return "Bot is running! 🚀"

if _name_ == "_main_":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 8080))