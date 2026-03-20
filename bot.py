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

# Список усіх тестів
ALL_TESTS = ["Тест 1", "Тест 2", "Тест 3"]

# Дані користувачів
user_data = {}
# Статистика по всіх тестах
user_stats = {}

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
    user_id = update.effective_user.id
    keyboard = [ALL_TESTS[:2], ALL_TESTS[2:]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Якщо користувач раніше зберіг прогрес, даємо кнопку продовжити
    if user_id in user_data and user_data[user_id].get("paused"):
        keyboard.append(["Продовжуємо"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text("Обери тест:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # ------------------ Продовження паузи ------------------
    if text == "Продовжуємо" and user_id in user_data and user_data[user_id].get("paused"):
        data = user_data[user_id]
        data["paused"] = False
        current_index = data["index"]
        question = data["questions"][current_index]["question"]
        # Відображаємо клавіатуру з іншими тестами
        other_tests = [t for t in ALL_TESTS if t != data["current_test"]]
        keyboard = [[t] for t in other_tests] + [["Поки що все"], ["Статистика"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(question, reply_markup=reply_markup)
        return

    # ------------------ Статистика ------------------
    if text == "Статистика":
        stats = user_stats.get(user_id, {})
        msg = "📊 Статистика твоїх тестів:\n"
        for test in ALL_TESTS:
            done, total = stats.get(test, (0, 0))
            msg += f"{test}: {done} з {total}\n"
        await update.message.reply_text(msg)
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
            "paused": False
        }
        # Встановлюємо загальну кількість питань для статистики
        if user_id not in user_stats:
            user_stats[user_id] = {}
        user_stats[user_id][text] = (0, len(questions))
        await update.message.reply_text("Починаємо тест!\n\n" + questions[0]["question"])
        return

    # ------------------ Якщо тест ще не обраний ------------------
    if user_id not in user_data:
        await update.message.reply_text("Натисни /start і обери тест")
        return

    # ------------------ Обробка кнопок повтору ------------------
    data = user_data[user_id]
    if "repeat_options" in data:
        if text == "Пройти тест ще раз":
            data["questions"] = data["all_questions"][:]
            random.shuffle(data["questions"])
            data["index"] = 0
            data["score"] = 0
            data["wrong"] = []
            del data["repeat_options"]
            other_tests = [t for t in ALL_TESTS if t != data["current_test"]]
            keyboard = [[t] for t in other_tests] + [["Поки що все"], ["Статистика"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("Починаємо тест знову!\n\n" + data["questions"][0]["question"], reply_markup=reply_markup)
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
            other_tests = [t for t in ALL_TESTS if t != data["current_test"]]
            keyboard = [[t] for t in other_tests] + [["Поки що все"], ["Статистика"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("Повторюємо тільки помилки!\n\n" + data["questions"][0]["question"], reply_markup=reply_markup)
            return

    # ------------------ Обробка відповіді ------------------
    current_index = data["index"]
    question = data["questions"][current_index]
    if text.upper() == question["answer"]:
        data["score"] += 1
        await update.message.reply_text("✅ Правильно!")
    else:
        await update.message.reply_text(f"❌ Неправильно! Правильна відповідь: {question['answer']}")
        data["wrong"].append(question)

    # ------------------ Наступне питання або завершення ------------------
    data["index"] += 1
    if data["index"] < len(data["questions"]):
        # клавіатура з іншими тестами
        other_tests = [t for t in ALL_TESTS if t != data["current_test"]]
        keyboard = [[t] for t in other_tests] + [["Поки що все"], ["Статистика"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(data["questions"][data["index"]]["question"], reply_markup=reply_markup)
    else:
        # Тест завершено
        await update.message.reply_text(f"🎉 Тест завершено!\nРезультат: {data['score']}/{len(data['questions'])}")
        # Оновлюємо статистику
        user_stats[user_id][data["current_test"]] = (data["score"], len(data["questions"]))
        # Пропонуємо повторити або інші тести
        keyboard = [["Пройти тест ще раз"]]
        if data["wrong"]:
            keyboard.insert(0, ["Повторити помилки"])
        other_tests = [t for t in ALL_TESTS if t != data["current_test"]]
        for t in other_tests:
            keyboard.append([t])
        keyboard.append(["Поки що все"])
        keyboard.append(["Статистика"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Що хочеш зробити далі?", reply_markup=reply_markup)
        data["repeat_options"] = True  # маркер того, що чекаємо на вибір користувача

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
