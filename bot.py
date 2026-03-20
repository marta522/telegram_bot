import os
import random
from flask import Flask, request
from waitress import serve
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8732864420:AAFgNLzg5GKJ8F63anr_SmKPygpRvSX27Tc"
WEBHOOK_PATH = f"/webhook/{TOKEN}"

user_data = {}

# ------------------ Функції бота ------------------

def load_questions(filename):
    questions = []
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read().strip().split("\n\n")
        for block in content:
            lines = block.strip().split("\n")
            q_text = "\n".join(lines[:-1])
            answer = lines[-1].replace("ANSWER:", "").strip().upper()
            questions.append({"question": q_text, "answer": answer})
    return questions

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Тест 1", "Тест 2"], ["Тест 3"]]
    reply_markup = update.message.reply_markup = None
    from telegram import ReplyKeyboardMarkup
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    user_data.pop(update.effective_user.id, None)
    await update.message.reply_text("Обери тест:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text in ["Тест 1", "Тест 2", "Тест 3"]:
        file = f"{text.lower().replace(' ', '')}.txt"
        questions = load_questions(file)
        random.shuffle(questions)
        user_data[user_id] = {"questions": questions, "index": 0, "score": 0}
        await update.message.reply_text("Починаємо тест!\n\n" + questions[0]["question"])
        return

    if user_id not in user_data:
        await update.message.reply_text("Натисни /start і обери тест")
        return

    data = user_data[user_id]
    current = data["index"]
    questions = data["questions"]
    correct = questions[current]["answer"]

    if text.upper() == correct:
        data["score"] += 1
        await update.message.reply_text("✅ Правильно!")
    else:
        await update.message.reply_text(f"❌ Неправильно! Правильна відповідь: {correct}")

    data["index"] += 1
    if data["index"] < len(questions):
        await update.message.reply_text(questions[data["index"]]["question"])
    else:
        await update.message.reply_text(f"🎉 Тест завершено!\nРезультат: {data['score']}/{len(questions)}")
        del user_data[user_id]

# ------------------ Flask сервер ------------------

flask_app = Flask(__name__)

# Ініціалізація Telegram Bot і Dispatcher
bot = Bot(TOKEN)
app_bot = ApplicationBuilder().token(TOKEN).build()
dispatcher = app_bot.dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@flask_app.route("/")
def home():
    return "Bot is running!"

@flask_app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    """Обробка Telegram webhook POST"""
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.run_async(dispatcher.process_update(update))
    return "OK"

# ------------------ Запуск ------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Встановлюємо Webhook у Telegram
    public_url = os.environ.get("RENDER_EXTERNAL_URL")
    if public_url:
        bot.set_webhook(f"{public_url}{WEBHOOK_PATH}")
        print("Webhook set to:", f"{public_url}{WEBHOOK_PATH}")
    # Запускаємо Flask через Waitress
    serve(flask_app, host="0.0.0.0", port=port)
