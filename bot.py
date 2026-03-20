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
user_data = {}  # дані користувачів
stats = {}      # статистика користувачів

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
    user_data.pop(update.effective_user.id, None)
    await update.message.reply_text("Обери тест:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # ------------------ Кнопки управління ------------------
    if text == "Статистика":
        user_stats = stats.get(str(user_id), {})
        output = []
        for i in range(1, 4):
            done = user_stats.get(f"test{i}_done", 0)
            total = user_stats.get(f"test{i}_all", 0)
            output.append(f"Тест{i}: {done} з {total}")
        await update.message.reply_text("\n".join(output))
        return

    if user_id in user_data and user_data[user_id].get("paused"):
        data = user_data[user_id]
        if text == "Продовжити":
            data.pop("paused")
            keyboard = [["Тест 1", "Тест 2"], ["Тест 3"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("Обери тест:", reply_markup=reply_markup)
            return
        else:
            await update.message.reply_text("Натисни 'Продовжити', щоб обрати тест.")
            return

    if user_id in user_data and "repeat_options" in user_data[user_id]:
        data = user_data[user_id]
        if text == "Пройти тест ще раз":
            data["questions"] = data["all_questions"][:]
            random.shuffle(data["questions"])
            data["index"] = 0
            data["score"] = 0
            data["wrong"] = []
            del data["repeat_options"]
            await update.message.reply_text("Починаємо тест знову!\n\n" + data["questions"][0]["question"])
            return
        elif text == "Повторити помилки":
            if not data["wrong"]:
                await update.message.reply_text("Немає помилок для повтору. Пройдемо тест заново.")
                data["questions"] = data["all_questions"][:]
            else:
                data["questions"] = data["wrong"][:]
            random.shuffle(data["questions"])
            data["index"] = 0
            data["score"] = 0
            data["wrong"] = []
            del data["repeat_options"]
            await update.message.reply_text("Повторюємо тільки помилки!\n\n" + data["questions"][0]["question"])
            return

    # ------------------ Вибір тесту ------------------
    if text in ["Тест 1", "Тест 2", "Тест 3"]:
        file = f"test{text[-1]}.txt"
        if not os.path.exists(file):
            await update.message.reply_text(f"Файл {file} не знайдено!")
            return
        questions = load_questions(file)
        random.shuffle(questions)
        user_data[user_id] = {
            "all_questions": questions[:],
            "questions": questions[:],
            "index": 0,
            "score": 0,
            "wrong": [],
        }
        await update.message.reply_text("Починаємо тест!\n\n" + questions[0]["question"])
        return

    # ------------------ Якщо тест ще не обраний ------------------
    if user_id not in user_data:
        await update.message.reply_text("Натисни /start і обери тест")
        return

    # ------------------ Кнопка Поки що все ------------------
    if text == "Поки що все":
        data = user_data[user_id]
        data["paused"] = True
        keyboard = [["Продовжити"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Перерва! Натисни 'Продовжити', коли будеш готовий.", reply_markup=reply_markup)
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
        data["wrong"].append(questions[current])

    # ------------------ Наступне питання або завершення ------------------
    data["index"] += 1
    if data["index"] < len(questions):
        # додаємо кнопки вибору тестів + статистику + поки що все
        keyboard = [["Тест 1", "Тест 2"], ["Тест 3"], ["Статистика", "Поки що все"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(questions[data["index"]]["question"], reply_markup=reply_markup)
    else:
        await update.message.reply_text(f"🎉 Тест завершено!\nРезультат: {data['score']}/{len(questions)}")
        # Запам’ятовуємо статистику
        user_stats = stats.setdefault(str(user_id), {})
        key_done = f"test{questions[0]['question'][-1]}_done"  # можна покращити підрахунок
        key_all = f"test{questions[0]['question'][-1]}_all"
        user_stats[key_done] = data["score"]
        user_stats[key_all] = len(questions)
        # Пропонуємо повторити або інші тести
        keyboard = [["Пройти тест ще раз", "Поки що все"], ["Повторити помилки"], ["Тест 1", "Тест 2", "Тест 3"], ["Статистика"]]
        # прибираємо вибір поточного тесту для кнопок
        current_test = data["all_questions"][0]["question"][-1]
        keyboard[2] = [t for t in keyboard[2] if t != f"Тест {current_test}"]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Що хочеш зробити далі?", reply_markup=reply_markup)
        data["repeat_options"] = True
