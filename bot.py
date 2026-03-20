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
ALL_TESTS = ["Тест 1", "Тест 2", "Тест 3"]

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
    keyboard = [ALL_TESTS]
    # Додаємо кнопку "Продовжуємо", якщо є незавершений тест
    if update.effective_user.id in user_data and user_data[update.effective_user.id].get("paused"):
        keyboard.append(["Продовжуємо"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Обери тест:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # ------------------ Продовження незавершеного тесту ------------------
    if text == "Продовжуємо":
        data = user_data[user_id]
        if "paused" in data and data["paused"]:
            data["paused"] = False
            await update.message.reply_text(
                f"Продовжуємо {data['current_test']}!\n\n" + 
                data["questions"][data["index"]]["question"]
            )
            return

    # ------------------ Статистика ------------------
    if text == "Статистика":
        stats_msg = []
        data = user_data.get(user_id, {})
        for test in ALL_TESTS:
            if "stats" in data and test in data["stats"]:
                correct, total = data["stats"][test]
                stats_msg.append(f"{test}: {correct}/{total}")
            else:
                stats_msg.append(f"{test}: 0/0")
        await update.message.reply_text("📊 Статистика по тестах:\n" + "\n".join(stats_msg))
        return

    # ------------------ Кнопка "Поки що все" ------------------
    if text == "Поки що все" and user_id in user_data:
        user_data[user_id]["paused"] = True
        await update.message.reply_text("Прогрес збережено. Щоб продовжити, натисни /start та 'Продовжуємо'.")
        return

    # ------------------ Обробка кнопок повтору після завершення ------------------
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
        elif text in ALL_TESTS:
            # Вибір іншого тесту під час завершення
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
                "stats": data.get("stats", {})
            }
            await update.message.reply_text(f"Починаємо {text}!\n\n" + questions[0]["question"])
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
            "stats": user_data.get(user_id, {}).get("stats", {})
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
        data["wrong"].append(questions[current])

    # ------------------ Наступне питання або завершення ------------------
    data["index"] += 1
    if data["index"] < len(questions):
        keyboard = [["Поки що все"], ["Статистика"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(questions[data["index"]]["question"], reply_markup=reply_markup)
    else:
        # Зберігаємо статистику
        if "stats" not in data:
            data["stats"] = {}
        data["stats"][data["current_test"]] = (data["score"], len(questions))

        await update.message.reply_text(f"🎉 Тест завершено!\nРезультат: {data['score']}/{len(questions)}")

        # Пропонуємо повторити або вибрати інший тест
        keyboard = []
        if data["wrong"]:
            keyboard.append(["Повторити помилки"])
        keyboard.append(["Пройти тест ще раз"])
        other_tests = [t for t in ALL_TESTS if t != data["current_test"]]
        for t in other_tests:
            keyboard.append([t])
        keyboard.append(["Статистика"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Що хочеш зробити далі?", reply_markup=reply_markup)
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
