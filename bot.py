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

logging.basicConfig(level=logging.INFO)

TESTS = ["Тест 1", "Тест 2", "Тест 3"]

# ------------------ ФУНКЦІЇ ------------------

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


def get_keyboard(current_test=None, paused=False):
    keyboard = []

    if paused:
        keyboard.append(["Продовжуємо"])
    else:
        for t in TESTS:
            if t != current_test:
                keyboard.append([t])
        keyboard.append(["Поки що все"])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ------------------ START ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Тест 1", "Тест 2"], ["Тест 3"]]
    await update.message.reply_text(
        "Обери тест:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ------------------ HANDLE ------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_data:
        user_data[user_id] = {}

    # ------------------ ПРОДОВЖИТИ ------------------
    if text == "Продовжуємо":
        current_test = user_data[user_id].get("active_test")

        if not current_test:
            await update.message.reply_text("Немає активного тесту.")
            return

        data = user_data[user_id][current_test]

        if data["index"] >= len(data["questions"]):
            await update.message.reply_text("Тест вже завершено.")
            return

        data["paused"] = False

        await update.message.reply_text(
            "Продовжуємо:\n\n" + data["questions"][data["index"]]["question"],
            reply_markup=get_keyboard(current_test)
        )
        return

    # ------------------ ВИБІР ТЕСТУ ------------------
    if text in TESTS:
        current_test = text
        user_data[user_id]["active_test"] = current_test

        if current_test not in user_data[user_id]:
            file = f"test{current_test[-1]}.txt"

            if not os.path.exists(file):
                await update.message.reply_text(f"Файл {file} не знайдено!")
                return

            questions = load_questions(file)
            random.shuffle(questions)

            user_data[user_id][current_test] = {
                "questions": questions,
                "all_questions": questions[:],
                "index": 0,
                "score": 0,
                "wrong": [],
                "paused": False
            }

        data = user_data[user_id][current_test]

        if data["index"] >= len(data["questions"]):
            await update.message.reply_text("Тест вже завершено. Обери дію нижче.")
            return

        await update.message.reply_text(
            data["questions"][data["index"]]["question"],
            reply_markup=get_keyboard(current_test)
        )
        return

    # ------------------ ПАУЗА ------------------
    if text == "Поки що все":
        current_test = user_data[user_id].get("active_test")

        if not current_test:
            return

        data = user_data[user_id][current_test]
        data["paused"] = True

        await update.message.reply_text(
            "⏸️ Пауза. Натисни 'Продовжуємо', щоб повернутись.",
            reply_markup=get_keyboard(paused=True)
        )
        return

    # ------------------ ПОВТОРИТИ ПОМИЛКИ ------------------
    if text == "Повторити помилки":
        last_test = user_data[user_id].get("last_finished_test")

        if not last_test:
            await update.message.reply_text("Немає тесту для повтору.")
            return

        data = user_data[user_id][last_test]

        if not data["wrong"]:
            await update.message.reply_text("Немає помилок 🎉")
            return

        data["questions"] = data["wrong"][:]
        random.shuffle(data["questions"])
        data["index"] = 0
        data["score"] = 0
        data["wrong"] = []
        data["paused"] = False

        user_data[user_id]["active_test"] = last_test

        await update.message.reply_text(
            "Повторюємо помилки:\n\n" + data["questions"][0]["question"],
            reply_markup=get_keyboard(last_test)
        )
        return

    # ------------------ ПРОЙТИ ЩЕ РАЗ ------------------
    if text == "Пройти тест ще раз":
        last_test = user_data[user_id].get("last_finished_test")

        if not last_test:
            return

        data = user_data[user_id][last_test]

        data["questions"] = data["all_questions"][:]
        random.shuffle(data["questions"])
        data["index"] = 0
        data["score"] = 0
        data["wrong"] = []
        data["paused"] = False

        user_data[user_id]["active_test"] = last_test

        await update.message.reply_text(
            "Починаємо заново:\n\n" + data["questions"][0]["question"],
            reply_markup=get_keyboard(last_test)
        )
        return

    # ------------------ ВІДПОВІДЬ ------------------
    current_test = user_data[user_id].get("active_test")

    if not current_test:
        await update.message.reply_text("Обери тест.")
        return

    data = user_data[user_id][current_test]

    if data["paused"]:
        await update.message.reply_text("Натисни 'Продовжуємо'.")
        return

    if data["index"] >= len(data["questions"]):
        await update.message.reply_text("Тест вже завершено.")
        return

    correct = data["questions"][data["index"]]["answer"]

    if text.upper() == correct:
        data["score"] += 1
        await update.message.reply_text("✅ Правильно!")
    else:
        await update.message.reply_text(f"❌ Неправильно! Правильна: {correct}")
        data["wrong"].append(data["questions"][data["index"]])

    data["index"] += 1

    if data["index"] < len(data["questions"]):
        await update.message.reply_text(
            data["questions"][data["index"]]["question"],
            reply_markup=get_keyboard(current_test)
        )
    else:
        await update.message.reply_text(
            f"🎉 Тест {current_test} завершено!\n{data['score']}/{len(data['questions'])}"
        )

        user_data[user_id]["last_finished_test"] = current_test

        keyboard = []
        if data["wrong"]:
            keyboard.append(["Повторити помилки"])
        keyboard.append(["Пройти тест ще раз"])

        other_tests = [t for t in TESTS if t != current_test]
        keyboard.append(other_tests)

        await update.message.reply_text(
            "Що далі?",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

        data["paused"] = True
        data["index"] = len(data["questions"])

# ------------------ WEBHOOK ------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    public_url = os.environ.get("RENDER_EXTERNAL_URL")

    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app_bot.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{public_url}/{TOKEN}"
    )
