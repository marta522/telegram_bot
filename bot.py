import os
import random
import logging
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

# ------------------ Налаштування логування ------------------
logging.basicConfig(level=logging.INFO)

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
    user_data.pop(update.effective_user.id, None)  # очищаємо попередні дані
    await update.message.reply_text("Обери тест:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # ------------------ Вибір тесту ------------------
    if text in ["Тест 1", "Тест 2", "Тест 3"]:
        file = f"test{text[-1]}.txt"  # test1.txt, test2.txt, test3.txt
        if not os.path.exists(file):
            await update.message.reply_text(f"Файл {file} не знайдено!")
            return
        questions = load_questions(file)
        random.shuffle(questions)
        user_data[user_id] = {
            "questions": questions,
            "index": 0,
            "score": 0,
            "wrong": []
        }
        await update.message.reply_text("Починаємо тест!\n\n" + questions[0]["question"])
        return

    # ------------------ Якщо тест ще не обраний ------------------
    if user_id not in user_data:
        await update.message.reply_text("Натисни /start і обери тест")
        return

    # ------------------ Обробка відповіді ------------------
    data = user_data[user_id]
    current = data["index"]
    questions = data["questions"]
    correct = questions[current]["answer"]

    if text.upper() == correct:
        data["score"] += 1
        await update.message.reply_text("✅ Правильно!")
    else:
        await update.message.reply_text(f"❌ Неправильно! Правильна відповідь: {correct}")
        data["wrong"].append(questions[current])  # додаємо помилку

    # ------------------ Перехід до наступного питання ------------------
    data["index"] += 1
    if data["index"] < len(questions):
        await update.message.reply_text(questions[data["index"]]["question"])
    else:
        # ------------------ Тест завершено ------------------
        result_text = f"🎉 Тест завершено!\nРезультат: {data['score']}/{len(questions)}"
        await update.message.reply_text(result_text)

        # ------------------ Пропонуємо повторити ------------------
        if data["wrong"]:
            keyboard = [["Повторити помилки"], ["Пройти тест ще раз"]]
        else:
            keyboard = [["Пройти тест ще раз"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Що хочеш зробити далі?", reply_markup=reply_markup)

        # ------------------ Обробка повторного запуску ------------------
        def reset_questions(repeat_wrong=False):
            if repeat_wrong:
                data["questions"] = data["wrong"]
                data["wrong"] = []
            else:
                file_index = questions[0]["question"].split("\n")[0][-1]  # беремо номер тесту
                file = f"test{file_index}.txt"
                data["questions"] = load_questions(file)
            random.shuffle(data["questions"])
            data["index"] = 0
            data["score"] = 0

        # Очікуємо вибір користувача
        data["awaiting_restart"] = True
        data["reset_func"] = reset_questions

        del user_data[user_id]["questions_done"]  # якщо потрібно очищаємо для нової сесії

    # ------------------ Обробка кнопок повтору ------------------
    if "awaiting_restart" in data and data["awaiting_restart"]:
        if text == "Пройти тест ще раз":
            data["reset_func"](repeat_wrong=False)
            data.pop("awaiting_restart")
            await update.message.reply_text("Починаємо тест знову!\n\n" + data["questions"][0]["question"])
        elif text == "Повторити помилки":
            data["reset_func"](repeat_wrong=True)
            data.pop("awaiting_restart")
            await update.message.reply_text("Повторюємо тільки помилки!\n\n" + data["questions"][0]["question"])
