import json
import random
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

CARDS_REQUESTED_SINCE_START = 0

TOKEN_FILE = "access_token.txt"
JSON_FILE = "tarot_cards.json"
IMAGES_DIR = "rider-waite-tarot"

with open(JSON_FILE, "r", encoding="utf-8") as f:
    TAROT_CARDS = json.load(f)

with open(TOKEN_FILE, "r") as f:
    TOKEN = f.read().replace('\n', '')

# Store daily cards per user: {user_id: {date: card_index}}
DAILY_CARDS = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Я бот Таро. Напиши /card, чтобы получить карту дня и её предсказание, или /anycard для случайной карты.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"С последнего запуска запрошено карт: {CARDS_REQUESTED_SINCE_START}.")

async def card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global CARDS_REQUESTED_SINCE_START
    CARDS_REQUESTED_SINCE_START += 1

    user_id = update.effective_user.id
    message_time = update.message.date
    user_date = message_time.date().isoformat()

    # Check if user already has a card for today
    if user_id not in DAILY_CARDS or DAILY_CARDS[user_id].get('date') != user_date:
        card_index = random.randint(0, len(TAROT_CARDS) - 1)
        DAILY_CARDS[user_id] = {'date': user_date, 'card_index': card_index}
    else:
        card_index = DAILY_CARDS[user_id]['card_index']

    card = TAROT_CARDS[card_index]
    await send_card_message(update, card, "Карта дня: ")

async def anycard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global CARDS_REQUESTED_SINCE_START
    CARDS_REQUESTED_SINCE_START += 1

    card_index = random.randint(0, len(TAROT_CARDS) - 1)
    card = TAROT_CARDS[card_index]
    await send_card_message(update, card)

async def send_card_message(update: Update, card: dict, message: str = '') -> None:
    message += f"{card['name']}\n\n{card['meaning']}"
    
    success = False
    image_name = card.get('image')
    if image_name:
        image_path = os.path.join(IMAGES_DIR, image_name)
        if os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                success = True
                await update.message.reply_photo(photo=photo, caption=message)

    if not success:
        await update.message.reply_text(message)

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("card", card))
    application.add_handler(CommandHandler("anycard", anycard))

    allowed_updates=[Update.MESSAGE]
    application.run_polling(allowed_updates=allowed_updates)

if __name__ == "__main__":
    main()