import json
import random
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from groq import Groq
import asyncio

CARDS_REQUESTED_SINCE_START = 0
QUESTIONS_ASKED_SINCE_START = 0

TOKEN_FILE = "access_token.txt"
JSON_FILE = "tarot_cards.json"
IMAGES_DIR = "rider-waite-tarot"

# Load configuration
with open(JSON_FILE, "r", encoding="utf-8") as f:
    TAROT_CARDS = json.load(f)

# Read Telegram token and Groq API key from token file
with open(TOKEN_FILE, "r") as f:
    lines = f.readlines()
    if len(lines) < 2:
        raise ValueError("access_token.txt must contain at least two lines: Telegram token and Groq API key")
    TELEGRAM_TOKEN = lines[0].strip()
    GROQ_API_KEY = lines[1].strip()

# Initialize Groq client
if not GROQ_API_KEY:
    raise ValueError("Groq API key is empty")
groq_client = Groq(api_key=GROQ_API_KEY)

# Store daily cards per user: {user_id: {date: {card_index}}}
DAILY_CARDS = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот Таро. Команды:\n"
        "/card - получить карту дня\n"
        "/anycard - случайная карта\n"
        "/question <вопрос> - задать вопрос (до 20 слов)\n"
        "/stats - статистика"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"С последнего запуска:\n"
        f"Запрошено карт: {CARDS_REQUESTED_SINCE_START}\n"
        f"Задано вопросов: {QUESTIONS_ASKED_SINCE_START}"
    )

async def card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global CARDS_REQUESTED_SINCE_START
    CARDS_REQUESTED_SINCE_START += 1

    user_id = update.effective_user.id
    message_time = update.message.date
    user_date = message_time.date().isoformat()

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

async def question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global QUESTIONS_ASKED_SINCE_START
    user_id = update.effective_user.id
    message_time = update.message.date
    user_date = message_time.date().isoformat()

    # Get question from command
    if not context.args:
        await update.message.reply_text("Пожалуйста, задайте вопрос после команды /question")
        return

    question = ' '.join(context.args)
    # Check word count
    word_count = len(question.split())
    if word_count > 20:
        await update.message.reply_text("Вопрос слишком длинный! Максимум 20 слов.")
        return

    QUESTIONS_ASKED_SINCE_START += 1

    # Draw a random card
    card_index = random.randint(0, len(TAROT_CARDS) - 1)
    card = TAROT_CARDS[card_index]

    # Prepare Groq API call with card context
    system_prompt = (
        "Вы мудрый таролог, отвечающий на вопросы пользователей с мистической проницательностью. "
        "Для ответа вытянута карта Таро: {card_name}. "
        "Включите энергию этой карты в свой ответ. "
        "Давайте краткие, содержательные ответы (50-70 слов), связанные с мудростью Таро. "
        "Используйте простой язык, избегайте сложных терминов."
    ).format(card_name=card['name'])

    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                max_completion_tokens=200,  # Conservative token limit for free tier
                temperature=0.7,
                stream=False
            )
        )
        
        answer = response.choices[0].message.content
        message = f"Карта: {card['name']}\nОтвет на ваш вопрос:\n{answer}"

        # Send response with card image
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

    except groq_client.APIConnectionError:
        await update.message.reply_text("Не могу уловить связь со вселенной. Попробуйте завтра.")
    except groq_client.RateLimitError:
        await update.message.reply_text("Мне нужно больше энергии чтобы ответить на вопрос. Попробуйте завтра.")
    except Exception:
        await update.message.reply_text(f"Вы отвергнуты вселенной.")

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
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("card", card))
    application.add_handler(CommandHandler("anycard", anycard))
    application.add_handler(CommandHandler("question", question))

    allowed_updates=[Update.MESSAGE]
    application.run_polling(allowed_updates=allowed_updates)

if __name__ == "__main__":
    main()