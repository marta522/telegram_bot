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

    # ------------------ Кнопки перерви та повтору ------------------
    if user_id in user_data:
        data = user_data[user_id]

        if text == "Поки що все":
            data["paused"] = True
            keyboard = [["Продовжуємо"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                "Тест поставлено на паузу. Продовжити можна пізніше.", 
                reply_markup=reply_markup
            )
            return

        if text == "Продовжуємо" and data.get("paused"):
            data["paused"] = False
            await update.message.reply_text("Продовжуємо тест!")
            await update.message.reply_text(data["questions"][data["index"]]["question"])
            return

        if text == "Пройти тест ще раз":
            data["questions"] = data["all_questions"][:]
            random.shuffle(data["questions"])
            data["index"] = 0
            data["score"] = 0
            data["wrong"] = []
            data.pop("repeat_options", None)
            await update.message.reply_text("Починаємо тест знову!\n\n" + data["questions"][0]["question"])
            return

        if text == "Повторити помилки":
            if not data["wrong"]:
                await update.message.reply_text("Немає помилок для повтору. Пройдемо тест заново.")
                data["questions"] = data["all_questions"][:]
            else:
                data["questions"] = data["wrong"][:]
            random.shuffle(data["questions"])
            data["index"] = 0
            data["score"] = 0
            data["wrong"] = []
            data.pop("repeat_options", None)
            await update.message.reply_text("Повторюємо тільки помилки!\n\n" + data["questions"][0]["question"])
            return

        if text == "Статистика":
            stats = []
            for t_name, t_data in data.get("completed_tests", {}).items():
                stats.append(f"{t_name}: {t_data['score']}/{t_data['total']}")
            stats_text = "\n".join(stats) if stats else "Ще немає пройдених тестів."
            await update.message.reply_text(f"📊 Статистика:\n{stats_text}")
            return

    # ------------------ Вибір тесту ------------------
    if text in ["Тест 1", "Тест 2", "Тест 3"]:
        file = f"test{text[-1]}.txt"
        if not os.path.exists(file):
            await update.message.reply_text(f"Файл {file} не знайдено!")
            return

        questions = load_questions(file)
        random.shuffle(questions)
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id].update({
            "current_test": text,
            "all_questions": questions[:],
            "questions": questions[:],
            "index": 0,
            "score": 0,
            "wrong": [],
            "paused": False
        })
        await update.message.reply_text(f"Починаємо {text}!\n\n" + questions[0]["question"])
        return

    # ------------------ Якщо тест ще не обраний ------------------
    if user_id not in user_data or user_data[user_id].get("paused", False):
        await update.message.reply_text("Натисни /start і обери тест або продовжимо тест пізніше")
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

    data["index"] += 1
    if data["index"] < len(questions):
        # Кнопки під час проходження тесту
        keyboard = [["Поки що все"], ["Тест 1", "Тест 2", "Тест 3"], ["Статистика"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(questions[data["index"]]["question"], reply_markup=reply_markup)
    else:
        # Завершення тесту
        completed_tests = data.setdefault("completed_tests", {})
        completed_tests[data["current_test"]] = {"score": data["score"], "total": len(data["questions"])}
        keyboard = [["Пройти тест ще раз"]]
        if data["wrong"]:
            keyboard.insert(0, ["Повторити помилки"])
        # Інші тести
        other_tests = [t for t in ["Тест 1", "Тест 2", "Тест 3"] if t != data["current_test"]]
        for t in other_tests:
            keyboard.append([t])
        keyboard.append(["Статистика", "Поки що все"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(f"🎉 Тест завершено!\nРезультат: {data['score']}/{len(questions)}", reply_markup=reply_markup)
        data["repeat_options"] = True

# ------------------ Запуск бота через webhook ------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    public_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not public_url:
        print("⚠️ Не знайдено RENDER_EXTERNAL_URL. Вебхук працювати не буде!")
        exit(1)

    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app_bot.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{public_url}/{TOKEN}"
    )
