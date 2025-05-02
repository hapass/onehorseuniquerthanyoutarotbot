import json
import random
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from groq import Groq
import asyncio

TOKEN_FILE = "access_token.txt"
JSON_FILE = "tarot_cards.json"
IMAGES_DIR = "rider-waite-tarot"

with open(JSON_FILE, "r", encoding="utf-8") as f:
    TAROT_CARDS = json.load(f)

with open(TOKEN_FILE, "r") as f:
    lines = f.readlines()
    if len(lines) < 2:
        raise ValueError("access_token.txt must contain at least two lines: Telegram token and Groq API key")
    TELEGRAM_TOKEN = lines[0].strip()
    GROQ_API_KEY = lines[1].strip()

if not GROQ_API_KEY:
    raise ValueError("Groq API key is empty")
groq_client = Groq(api_key=GROQ_API_KEY)

# Small in-memory database: { user_id: { card_date, card_index, question_date } }
USER_DATA = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот Таро и вот мои команды:\n"
        "/card - получить карту дня\n"
        "/anycard - получить случайную карту\n"
        "/question <вопрос> - задать вопрос (1 в день, до 100 символов)"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Уникальных пользователей с последнего запуска: {len(list(USER_DATA))}")

async def card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    message_time = update.message.date
    user_date = message_time.date().isoformat()

    if user_id not in USER_DATA or USER_DATA[user_id].get('card_date') != user_date:
        card_index = random.randint(0, len(TAROT_CARDS) - 1)
        USER_DATA[user_id] = {'card_date': user_date, 'card_index': card_index}
    else:
        card_index = USER_DATA[user_id]['card_index']

    card = TAROT_CARDS[card_index]
    await send_card_message(update, card, f"Карта дня: {card['name']}\n\n{card['meaning']}")

async def anycard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    card_index = random.randint(0, len(TAROT_CARDS) - 1)
    card = TAROT_CARDS[card_index]
    await send_card_message(update, card, f"{card['name']}\n\n{card['meaning']}")

async def question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    message_time = update.message.date
    user_date = message_time.date().isoformat()

    if user_id in USER_DATA and USER_DATA[user_id].get('question_date') == user_date:
        await update.message.reply_text("Извините, вы уже задавали вопрос сегодня. Попробуйте завтра!")
        return

    if not context.args:
        await update.message.reply_text("Пожалуйста, задайте вопрос после команды /question")
        return

    question = ' '.join(context.args)
    if question.strip() == "":
        await update.message.reply_text("Пожалуйста, задайте вопрос после команды /question")
        return

    symbol_count = len(question)
    if symbol_count > 100:
        await update.message.reply_text("Вопрос слишком длинный, я не смогу должным образом сфокусироваться. Пожалуйста, задайте вопрос максимум из 100 символов.")
        return

    USER_DATA[user_id] = {'question_date': user_date}

    card_index = random.randint(0, len(TAROT_CARDS) - 1)
    card = TAROT_CARDS[card_index]

    system_prompt = (
        "Вы мудрый таролог, отвечающий на вопросы пользователей с мистической проницательностью. "
        "Для ответа вытянута карта Таро: {card_name}. Больше тянуть карты вы не можете."
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
                max_completion_tokens=300,  # Conservative token limit for free tier
                temperature=0.7,
                stream=False
            )
        )

        await send_card_message(update, card, f"Карта: {card['name']}\n\nОтвет на ваш вопрос:\n{response.choices[0].message.content}")

    except groq_client.APIConnectionError:
        await update.message.reply_text("Не могу уловить связь со вселенной. Попробуйте завтра.")
    except groq_client.RateLimitError:
        await update.message.reply_text("Мне нужно больше энергии чтобы ответить на этот вопрос. Попробуйте завтра.")
    except Exception:
        await update.message.reply_text("Вы отвергнуты вселенной.")

async def send_card_message(update: Update, card: dict, message: str) -> None:
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