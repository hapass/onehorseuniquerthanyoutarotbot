import json
import random
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = ""

JSON_FILE = "tarot_cards.json"
IMAGES_DIR = "rider-waite-tarot"

with open(JSON_FILE, "r", encoding="utf-8") as f:
    TAROT_CARDS = json.load(f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот Таро. Напиши /card, чтобы получить карту дня и её предсказание."
    )

async def card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    card_id = str(random.randint(0, len(TAROT_CARDS) - 1))
    card = TAROT_CARDS[card_id]
    
    message = f"**Карта дня: {card['name']}**\n\n{card['meaning']}"
    
    image_name = card.get('image')
    if image_name:
        image_path = os.path.join(IMAGES_DIR, image_name)
        if os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                await update.message.reply_photo(photo=photo)
    
    await update.message.reply_text(message, parse_mode="Markdown")

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("card", card))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()