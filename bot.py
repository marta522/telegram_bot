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
    if not os.path.exists(filename):
        logging.warning(f"Файл {filename} не знайдено!")
        return questions
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
    logging.info(f"{update.effective_user.username} натиснув /start")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    logging.info(f"Отримано повідомлення від {user_id}: {text}")

    # ------------------ Обробка повторів / перерва ------------------
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
        elif text == "Поки що все":
            data["paused"] = True
            del data["repeat_options"]
            keyboard = [["Продовжуємо"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("Тест призупинено. Натисни 'Продовжуємо', щоб повернутись до тестів.", reply_markup=reply_markup)
            return

    # ------------------ Відновлення після паузи ------------------
    if user_id in user_data and user_data[user_id].get("paused") and text == "Продовжуємо":
        data = user_data[user_id]
        data.pop("paused")
        keyboard = [["Тест 1", "Тест 2"], ["Тест 3"], ["Статистика"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Вибери тест:", reply_markup=reply_markup)
        return

    # ------------------ Статистика ------------------
    if text == "Статистика":
        stats = []
        data = user_data.get(user_id, {})
        for i in range(1, 4):
            all_q = data.get(f"test{i}_all", 25)
            done_q = data.get(f"test{i}_done", 0)
            stats.append(f"Тест{i}: {done_q}/{all_q}")
        await update.message.reply_text("\n".join(stats))
        return

    # ------------------ Вибір тесту ------------------
    if text in ["Тест 1", "Тест 2", "Тест 3"]:
        file = f"test{text[-1]}.txt"
        questions = load_questions(file)
        if not questions:
            await update.message.reply_text(f"Файл {file} порожній або не знайдено!")
            return
        random.shuffle(questions)
        if user_id not in user_data:
            user_data[user_id] = {}
        data = user_data[user_id]
        data.update({
            "all_questions": questions[:],
            "questions": questions[:],
            "index": 0,
            "score": 0,
            "wrong": [],
            f"test{text[-1]}_all": len(questions),
            f"test{text[-1]}_done": 0
        })
        await update.message.reply_text("Починаємо тест!\n\n" + questions[0]["question"])
        return

    # ------------------ Обробка відповіді ------------------
    if user_id not in user_data or user_data[user_id].get("paused"):
        await update.message.reply_text("Натисни /start і обери тест")
        return

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
        await update.message.reply_text(questions[data["index"]]["question"])
    else:
        # зберігаємо результат тесту
        test_num = data["questions"][0]["question"].split()[0][-1]  # простий спосіб визначити тест
        data[f"test{test_num}_done"] = data.get(f"test{test_num}_done", 0) + data["score"]

        await update.message.reply_text(f"🎉 Тест завершено!\nРезультат: {data['score']}/{len(questions)}")
        keyboard = [["Повторити помилки", "Пройти тест ще раз"], ["Тест 1", "Тест 2", "Тест 3"], ["Статистика"], ["Поки що все"]]
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

    logging.info(f"Starting bot on port {port} with webhook {public_url}/{TOKEN}")
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app_bot.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{public_url}/{TOKEN}"
    )
