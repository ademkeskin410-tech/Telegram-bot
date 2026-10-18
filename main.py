import os
import re
import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# Logging ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- SQLite Veritabanı Kurulumu ---
DB_NAME = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warnings (
            chat_id INTEGER,
            user_id INTEGER,
            count INTEGER,
            PRIMARY KEY (chat_id, user_id)
        )
    ''')
    conn.commit()
    conn.close()

def get_warnings(chat_id: int, user_id: int) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?', (chat_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def add_warning(chat_id: int, user_id: int) -> int:
    current = get_warnings(chat_id, user_id) + 1
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO warnings (chat_id, user_id, count)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET count = ?
    ''', (chat_id, user_id, current, current))
    conn.commit()
    conn.close()
    return current

def reset_warnings(chat_id: int, user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM warnings WHERE chat_id = ? AND user_id = ?', (chat_id, user_id))
    conn.commit()
    conn.close()

# --- Küfür ve Hakaret Filtresi ---
BANNED_WORDS = [
    'aptal', 'beyinsiz', 'gerizekalı', 'salak', 'mal', 'şerefsiz', 'piç', 
    'oç', 'amk', 'aq', 'sik', 'yarrak', 'amcık', 'göt', 'ibne', 'kahpe',
    'orospu', 'yavşak', 'puşt', 'dalyarak'
]

def clean_text(text: str) -> str:
    """Türkçe karakterleri dönüştürür ve harf dışındaki karakterleri temizler."""
    tr_map = str.maketrans("çğıöşüİIĞÖŞÜ", "cgiosuigiosu")
    text = text.translate(tr_map).lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text

def contains_profanity(text: str) -> bool:
    cleaned = clean_text(text)
    words = cleaned.split()
    
    for banned in BANNED_WORDS:
        banned_clean = clean_text(banned)
        # 1. Kelime tam eşleşme kontrolü
        if banned_clean in words:
            return True
        # 2. Ağır hakaret/küfürlerin kelime içinde bitişik geçme durumu
        if len(banned_clean) > 3 and banned_clean in cleaned:
            return True
    return False

# --- Mesaj İşleyici (Handler) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    user = update.message.from_user
    if not user:
        return
    user_id = user.id
    username = user.username or user.first_name

    # 1. Yöneticileri Kontrol Et (Yöneticilere ceza uygulanmaz)
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in ['administrator', 'creator']:
            return
    except Exception:
        pass

    raw_text = update.message.text
    cleaned_text = clean_text(raw_text)

    # --- KURAL 3 & 4: Argo, Hakaret ve Küfür Filtresi ---
    if contains_profanity(raw_text):
        try:
            await update.message.delete()
        except Exception as e:
            logging.error(f"Mesaj silinemedi: {e}")

        warn_count = add_warning(chat_id, user_id)

        if warn_count == 1:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ @{username} (1/3 Uyarı)! Lütfen grupta argo, küfür ve hakaret kullanma."
            )
        elif warn_count == 2:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ @{username} (2/3 Uyarı)! Hakaret ve küfür devam ediyor. Tekrarında susturulacaksın."
            )
        else: # 3. İhlal
            reset_warnings(chat_id, user_id)
            until_date = datetime.now() + timedelta(hours=1) # 1 saat susturma
            try:
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⛔ @{username} (3/3 İhlal)! Tekrarlanan argo ve hakaret nedeniyle 1 saat boyunca susturuldun."
                )
            except Exception as e:
                logging.error(f"Kullanıcı susturulamadı: {e}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⛔ @{username} 3/3 ihlal sınırına ulaştı! (Yetki yetersiz olduğu için otomatik susturulamadı)."
                )
        return

    # --- KURAL 1: Lina İsmiyle Konuşma ve Hitap Algılama ---
    is_lina_mentioned = bool(re.search(r'\blina\b', cleaned_text))

    if is_lina_mentioned:
        if any(q in cleaned_text for q in ['nasilsin', 'ne yapiyorsun', 'napan', 'netyon']):
            await update.message.reply_text(f"İyiyim {user.first_name}, teşekkür ederim! Sen nasılsın? 😊")
            return
        elif any(s in cleaned_text for s in ['merhaba', 'selam', 'slm']):
            await update.message.reply_text(f"Merhaba {user.first_name}! Nasıl yardımcı olabilirim? ✨")
            return

    # --- Genel Selamlaşma Yanıtları ---
    if cleaned_text in ['selam', 'sa', 'slm', 'selamun aleykum']:
        await update.message.reply_text(f"Aleyküm selam 👋")
    elif cleaned_text in ['gunaydin', 'gunaydinlar']:
        await update.message.reply_text("Günaydın ☀️")
    elif cleaned_text in ['iyi aksamlar']:
        await update.message.reply_text("İyi akşamlar 🌆")
    elif cleaned_text in ['iyi geceler']:
        await update.message.reply_text("İyi geceler 🌙")

# --- KURAL 2: Gruba Yeni Katılan Üyeleri Karşılama ---
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue
        first_name = member.first_name
        await update.message.reply_text(
            f"Hoş geldin, {first_name}! 👋 Grubumuza hoş geldin, iyi sohbetler dileriz. 🖤"
        )

# --- Ana Çalıştırma Fonksiyonu ---
def main():
    init_db()

    # Doğrudan eklenen API Token
    token = 8996494642:AAHTcJ04dW43KDdEEfUp-9Zqv9M_anbs2gI

    application = ApplicationBuilder().token(token).build()

    # Dinleyiciler
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Lina Bot aktif ve çalışıyor...")
    application.run_polling()

if __name__ == '__main__':
    main()
