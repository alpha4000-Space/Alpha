# AlphaCoderXBot - Telegram + Claude API bot
# Python 3.10+ kerak

from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import requests
import os

# Telegram va Claude API tokenlarini environment variables dan oling
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Railway Environment Variable
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")      # Railway Environment Variable

CLAUDE_API_URL = "https://api.anthropic.com/v1/complete"  # Claude API endpoint

# Foydalanuvchi xabarlarini qabul qilish
def handle_message(update: Update, context: CallbackContext):
    text = update.message.text

    # Agar foydalanuvchi "kim yaratgan?" desа
    if "kim yaratgan" in text.lower():
        update.message.reply_text("AlphaCoder yaratgan 😎")
        return

    # Kod yozish uchun trigger: foydalanuvchi "kod" so'zini yozsa
    if "kod" in text.lower():
        update.message.reply_text("Kod generatsiya qilinyapti, biroz kuting...")
        prompt = f"Foydalanuvchi so‘radi: {text}\nKod yozing:"
        max_tokens = 2000  # uzun kod uchun token limitini oshirish mumkin
        generate_and_send_code(update, prompt, max_tokens)
    else:
        # Umumiy savollarga Claude API javob beradi
        prompt = f"Foydalanuvchi so‘radi: {text}\nJavob ber:"
        max_tokens = 500
        generate_and_send_text(update, prompt, max_tokens)

# Kod generatsiya qilish va fayl yuborish
def generate_and_send_code(update: Update, prompt, max_tokens):
    try:
        headers = {
            "Authorization": f"Bearer {CLAUDE_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "claude-2",
            "prompt": prompt,
            "max_tokens_to_sample": max_tokens,
            "temperature": 0.2
        }

        response = requests.post(CLAUDE_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        code_text = result.get("completion", "Kod topilmadi 😢")

        filename = "generated_code.py"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(code_text)

        with open(filename, "rb") as f:
            update.message.reply_document(InputFile(f, filename=filename))

    except Exception as e:
        update.message.reply_text(f"Xatolik yuz berdi: {str(e)}")

# Umumiy savollarga javob berish
def generate_and_send_text(update: Update, prompt, max_tokens):
    try:
        headers = {
            "Authorization": f"Bearer {CLAUDE_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "claude-2",
            "prompt": prompt,
            "max_tokens_to_sample": max_tokens,
            "temperature": 0.5
        }

        response = requests.post(CLAUDE_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        answer_text = result.get("completion", "Javob topilmadi 😢")
        update.message.reply_text(answer_text)

    except Exception as e:
        update.message.reply_text(f"Xatolik yuz berdi: {str(e)}")

# /start komandasi
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Salom! Men AlphaCoderXBotman 😎\n"
        "Sizga kod yozib beraman va umumiy savollarga javob beraman.\n"
        "Masalan: '800 qator Python bot kodi yoz' yoki oddiy savol bering."
    )

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
