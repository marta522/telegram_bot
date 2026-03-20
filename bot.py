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

def get_main_keyboard(current_test=None):
    keys = []
    tests = ["Тест 1", "Тест 2", "Тест 3"]
    test_buttons = [t for t in tests if t != current_test]
    if test_buttons:
        keys.append(test_buttons)
    keys.append(["Статистика"])
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)

# ------------------ Обробка команд ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Тест 1", "Тест 2"], ["Тест 3"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    user_data.pop(update.effective_user.id, None)
    await update.message.reply_text("Обери тест:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    data = user_data.get(user_id, {})

    # ------------------ Статистика ------------------
    if text == "Статистика":
        stats = []
        for t_name, t_data in data.get("completed_tests", {}).items():
            stats.append(f"{t_name}: {t_data['score']}/{t_data['total']}")
        stats_text = "\n".join(stats) if stats else "Ще немає пройдених тестів."
        await update.message.reply_text(f"📊 Статистика:\n{stats_text}")

        # Повернути до поточного питання, якщо тест триває
        if data.get("questions") and data.get("index") is not None:
            keyboard = [["Поки що все"], ["Статистика"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                "Продовжимо тест:\n\n" + data["questions"][data["index"]]["question"],
                reply_markup=reply_markup
            )
        return

    # ------------------ Продовження після паузи ------------------
    if data.get("paused") and text == "Продовжуємо":
        data["paused"] = False
        keyboard = [["Поки що все"], ["Статистика"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Продовжуємо тест:\n\n" + data["questions"][data["index"]]["question"],
            reply_markup=reply_markup
        )
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
            "paused": False,
            "current_test": text,
            "completed_tests": data.get("completed_tests", {})
        }
        keyboard = [["Поки що все"], ["Статистика"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Починаємо тест!\n\n" + questions[0]["question"],
            reply_markup=reply_markup
        )
        return

    # ------------------ Пауза ------------------
    if text == "Поки що все":
        data["paused"] = True
        keyboard = [["Продовжуємо"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("⏸️ Тест на паузі. Коли захочеш — натисни 'Продовжуємо'.", reply_markup=reply_markup)
        return

    # ------------------ Якщо тест ще не обраний ------------------
    if not data.get("questions"):
        await update.message.reply_text("Натисни /start і обери тест")
        return

    # ------------------ Обробка відповіді ------------------
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
        keyboard = [["Поки що все"], ["Статистика"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(questions[data["index"]]["question"], reply_markup=reply_markup)
    else:
        # Тест завершено
        test_name = data.get("current_test")
        if "completed_tests" not in data:
            data["completed_tests"] = {}
        data["completed_tests"][test_name] = {"score": data["score"], "total": len(questions)}

        await update.message.reply_text(f"🎉 Тест '{test_name}' завершено!\nРезультат: {data['score']}/{len(questions)}")

        # Пропонуємо дії після завершення
        keyboard = []
        if data["wrong"]:
            keyboard.append(["Повторити помилки"])
        keyboard.append(["Пройти тест ще раз"])
        other_tests = [t for t in ["Тест 1","Тест 2","Тест 3"] if t != test_name]
        keyboard.append(other_tests)
        keyboard.append(["Статистика"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Що хочеш зробити далі?", reply_markup=reply_markup)

        # Очищаємо поточний тест
        data["questions"] = None
        data["index"] = None
        data["score"] = 0
        data["wrong"] = []
        data["paused"] = False
        data["current_test"] = None

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
