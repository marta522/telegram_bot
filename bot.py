from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import random

TOKEN = "8732864420:AAFgNLzg5GKJ8F63anr_SmKPygpRvSX27Tc"

user_data = {}

# 📄 Завантаження тестів
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

# 🚀 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Тест 1", "Тест 2"],
        ["Тест 3"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # очищаємо попередній тест
    user_data.pop(update.effective_user.id, None)

    await update.message.reply_text("Обери тест:", reply_markup=reply_markup)

# 🎯 Вибір тесту або відповідь
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # 👉 ВИБІР ТЕСТУ
    if text in ["Тест 1", "Тест 2", "Тест 3"]:
        if text == "Тест 1":
            questions = load_questions("test1.txt")
        elif text == "Тест 2":
            questions = load_questions("test2.txt")
        else:
            questions = load_questions("test3.txt")

        # 🔀 перемішування
        random_questions = questions.copy()
        random.shuffle(random_questions)

        user_data[user_id] = {
            "questions": random_questions,
            "index": 0,
            "score": 0
        }

        await update.message.reply_text("Починаємо тест!\n\n" + random_questions[0]["question"])
        return

    # 👉 ЯКЩО КОРИСТУВАЧ НЕ ВИБРАВ ТЕСТ
    if user_id not in user_data:
        await update.message.reply_text("Натисни /start і обери тест")
        return

    # 👉 ОБРОБКА ВІДПОВІДІ
    user_answer = text.upper()
    data = user_data[user_id]
    current = data["index"]
    questions = data["questions"]

    correct = questions[current]["answer"]

    if user_answer == correct:
        data["score"] += 1
        await update.message.reply_text("✅ Правильно!")
    else:
        await update.message.reply_text(f"❌ Неправильно! Правильна відповідь: {correct}")

    data["index"] += 1

    # 👉 НАСТУПНЕ ПИТАННЯ
    if data["index"] < len(questions):
        next_q = questions[data["index"]]["question"]
        await update.message.reply_text(next_q)
    else:
        score = data["score"]
        total = len(questions)
        await update.message.reply_text(f"🎉 Тест завершено!\nРезультат: {score}/{total}")

        # очищаємо після завершення
        del user_data[user_id]

# ▶️ запуск
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()