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
ALL_TESTS = ["Тест 1", "Тест 2", "Тест 3"]

user_data = {}  # Зберігаємо дані кожного користувача
logging.basicConfig(level=logging.INFO)

# ------------------ Функції ------------------

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
    keyboard = [[t] for t in ALL_TESTS]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Обери тест:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # ------------------ Продовжуємо після паузи ------------------
    if user_id in user_data and user_data[user_id].get("paused") and text == "Продовжуємо":
        data = user_data[user_id]
        data["paused"] = False
        keyboard = [[t] for t in ALL_TESTS if t != data["current_test"]] + [["Поки що все"], ["Статистика"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("🟢 Продовжуємо тест!", reply_markup=reply_markup)
        await update.message.reply_text(data["questions"][data["index"]]["question"])
        return

    # ------------------ Статистика ------------------
    if text == "Статистика":
        stats = []
        if user_id in user_data:
            for test in ALL_TESTS:
                tdata = user_data[user_id].get("stats", {}).get(test, {})
                stats.append(f"{test}: {tdata.get('score', 0)} з {tdata.get('total', 0)}")
        else:
            stats = [f"{t}: 0 з 0" for t in ALL_TESTS]
        await update.message.reply_text("📊 Статистика:\n" + "\n".join(stats))
        return

    # ------------------ Поки що все ------------------
    if user_id in user_data and not user_data[user_id].get("paused") and text == "Поки що все":
        data = user_data[user_id]
        data["paused"] = True
        keyboard = [["Продовжуємо"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🛑 Тест зупинено. Твій прогрес збережено. Коли захочеш продовжити — натисни «Продовжуємо».",
            reply_markup=reply_markup
        )
        return

    # ------------------ Вибір тесту ------------------
    if text in ALL_TESTS:
        file = f"test{text[-1]}.txt"
        if not os.path.exists(file):
            await update.message.reply_text(f"Файл {file} не знайдено!")
            return
        questions = load_questions(file)
        random.shuffle(questions)
        user_data[user_id] = {
            "current_test": text,
            "all_questions": questions[:],
            "questions": questions[:],
            "index": 0,
            "score": 0,
            "wrong": [],
            "paused": False,
            "stats": user_data.get(user_id, {}).get("stats", {})
        }
        await update.message.reply_text("Починаємо тест!\n\n" + questions[0]["question"])
        return

    # ------------------ Якщо користувач ще не обрав тест ------------------
    if user_id not in user_data:
        await update.message.reply_text("Натисни /start і обери тест")
        return

    # ------------------ Обробка відповіді ------------------
    data = user_data[user_id]
    if data.get("paused"):
        await update.message.reply_text("Натисни «Продовжуємо», щоб продовжити тест")
        return

    current = data["index"]
    questions = data["questions"]
    correct = questions[current]["answer"]

    if text.upper() == correct:
        data["score"] += 1
        await update.message.reply_text("✅ Правильно!")
    else:
        await update.message.reply_text(f"❌ Неправильно! Правильна відповідь: {correct}")
        data["wrong"].append(questions[current])

    # ------------------ Наступне питання або завершення ------------------
    data["index"] += 1
    if data["index"] < len(questions):
        await update.message.reply_text(questions[data["index"]]["question"])
    else:
        # Зберігаємо статистику
        data["stats"][data["current_test"]] = {
            "score": data["score"],
            "total": len(questions)
        }
        await update.message.reply_text(f"🎉 Тест завершено!\nРезультат: {data['score']}/{len(questions)}")
        # Пропонуємо варіанти далі
        keyboard = []
        if data["wrong"]:
            keyboard.append(["Повторити помилки"])
        keyboard.append(["Пройти тест ще раз"])
        # Інші тести, крім поточного
        for t in ALL_TESTS:
            if t != data["current_test"]:
                keyboard.append([t])
        keyboard.append(["Статистика", "Поки що все"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Що хочеш зробити далі?", reply_markup=reply_markup)
        data["repeat_options"] = True  # маркер очікування вибору користувача
