import logging
from telegram import ChatPermissions, Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

YASAKLI_KELIMELER = ["kufur1", "kufur2", "argo1"]


async def yeni_uye_geldi(update: Update, context: ContextTypes.DEFAULT_TYPE):
  for member in update.message.new_chat_members:
    if member.id == context.bot.id:
      continue
    hos_geldin_mesaji = f"Selamün aleyküm {member.first_name}, hoş geldin!"
    await update.message.reply_text(hos_geldin_mesaji)


async def kufur_kontrol(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not update.message or not update.message.text:
    return

  mesaj_metni = update.message.text.lower()
  user = update.message.from_user
  chat = update.message.chat

  for kelime in YASAKLI_KELIMELER:
    if kelime in mesaj_metni:
      try:
        await update.message.delete()
        kisitlama = ChatPermissions(can_send_messages=False)
        await chat.restrict_member(
            user.id, permissions=kisitlama, until_date=600
        )
        await chat.send_message(
            f"@{user.username or user.first_name}, küfür/argo kullandığın"
            " için 10 dakika susturuldun!"
        )
      except Exception as e:
        print(f"Hata: {e}")
      break


def main():
  TOKEN = "8838540653:AAFbAIKXJlVIHeDWQtTe4-tSUKgm85HepPY"
  app = ApplicationBuilder().token(TOKEN).build()

  app.add_handler(
      MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, yeni_uye_geldi)
  )
  app.add_handler(
      MessageHandler(filters.TEXT & (~filters.COMMAND), kufur_kontrol)
  )

  print("Bot çalışıyor...")
  app.run_polling()


if __name__ == "__main__":
  main()
