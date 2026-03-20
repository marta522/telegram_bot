import os
import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

TOKEN = "8732864420:AAFgNLzg5GKJ8F63anr_SmKPygpRvSX27Tc"
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
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    user_data.pop(update.effective_user.id, None)
    await update.message.reply_text("Обери тест:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # ---------------- Вибір тесту ----------------
    if text in ["Тест 1", "Тест 2", "Тест 3"]:
        file = f"test{text[-1]}.txt"
        if not os.path.exists(file):
            await update.message.reply_text(f"Файл {file} не знайдено!")
            return

        questions = load_questions(file)
        random.shuffle(questions)

        user_data[user_id] = {
            "questions": questions,
            "index": 0,
            "score": 0,
            "wrong": []  # зберігаємо неправильні
        }

        await update.message.reply_text("Починаємо тест!\n\n" + questions[0]["question"])
        return

    # ---------------- Повтор неправильних ----------------
    if text == "Повторити помилки":
        data = user_data.get(user_id)
        if not data or not data.get("wrong"):
            await update.message.reply_text("Немає помилок для повторення 🙂")
            return

        data["questions"] = data["wrong"]
        data["wrong"] = []
        data["index"] = 0
        data["score"] = 0
        await update.message.reply_text("Повторюємо помилки!\n\n" + data["questions"][0]["question"])
        return

    # ---------------- Пройти ще раз ----------------
    if text == "Пройти ще раз":
        await start(update, context)
        return

    # ---------------- Якщо тест не обрано ----------------
    if user_id not in user_data:
        await update.message.reply_text("Натисни /start і обери тест")
        return

    # ---------------- Обробка відповіді ----------------
    data = user_data[user_id]
    current = data["index"]
    questions = data["questions"]
    correct = questions[current]["answer"]

    if text.upper() == correct:
        data["score"] += 1
        await update.message.reply_text("✅ Правильно!")
    else:
        await update.message.reply_text(f"❌ Неправильно! Правильна відповідь: {correct}")
        data["wrong"].append(questions[current])

    data["index"] += 1

    # ---------------- Наступне питання або результат ----------------
    if data["index"] < len(questions):
        await update.message.reply_text(questions[data["index"]]["question"])
    else:
        score = data["score"]
        total = len(questions)

        if data["wrong"]:  # якщо були помилки
            keyboard = [["Повторити помилки"], ["Пройти ще раз"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f"Тест завершено!\nРезультат: {score}/{total}\nХочеш повторити помилки?",
                reply_markup=reply_markup
            )
        else:  # якщо всі відповіді правильні
            keyboard = [["Пройти ще раз"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f"🎉 Ідеально! {score}/{total}\nМожеш пройти тест ще раз:",
                reply_markup=reply_markup
            )
