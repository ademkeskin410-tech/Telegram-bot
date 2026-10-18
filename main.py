import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Yasaklı kelimeler (küfür / argo filtresi)
BANNED_WORDS = ['sex', 'sik', 'amk', 'aq', 'oç', 'piç']

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.lower()
    user = update.message.from_user
    username = user.username or user.first_name

    # Küfür / Argo Filtresi
    if any(banned in text for banned in BANNED_WORDS):
        try:
            await update.message.delete()
            await update.message.reply_text(f"⚠️ @{username}, grupta bu tür ifadeler kullanmak yasaktır!")
        except Exception as e:
            logging.error(f"Mesaj silinemedi: {e}")
        return

    # Otomatik Karşılama ve Sohbet Yanıtları
    if text in ['selam', 'sa', 'selamün aleyküm', 'selamun aleykum']:
        await update.message.reply_text(f"Aleykümselam @{username}, hoş geldin! 👋")
    elif text in ['naber', 'nabersın', 'nasılsın']:
        await update.message.reply_text('İyiyim, teşekkür ederim! Sen nasılsın? 😊')

def main():
    # Doğrudan eklediğimiz token
    token = "8996494642:AAF3HC6lsJ2Mz1CJ2ZG8ejbjRbYPFEMhG80"

    application = ApplicationBuilder().token(token).build()

    # Metin mesajlarını filtre ve yanıtlar için dinle
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
