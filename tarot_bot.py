import json
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Токен бота (нужно заменить на ваш)
TOKEN = ""

# Загружаем карты из JSON-файла
with open("tarot_cards.json", "r", encoding="utf-8") as f:
    TAROT_CARDS = json.load(f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот Таро. Напиши /card, чтобы получить карту дня и её предсказание."
    )

async def card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Выбираем случайную карту
    card_id = str(random.randint(0, len(TAROT_CARDS) - 1))
    card = TAROT_CARDS[card_id]
    
    # Формируем сообщение
    message = f"🃏 **Карта дня: {card['name']}**\n\n{card['meaning']}"
    await update.message.reply_text(message, parse_mode="Markdown")

def main() -> None:
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("card", card))

    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()