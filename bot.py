import os
import random
import json
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
DATA_FILE = "user_data.json"
user_data = {}
logging.basicConfig(level=logging.INFO)

# ------------------ Завантаження/збереження ------------------
def load_user_data():
    global user_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            user_data = json.load(f)
    else:
        user_data = {}

def save_user_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False)

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
    keyboard = [["Тест 1", "Тест 2"], ["Тест 3"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    user_id = str(update.effective_user.id)
    if user_id in user_data:
        # При старті дозволяємо продовжити перерваний тест
        data = user_data[user_id]
        if data.get("paused"):
            keyboard = [["Продовжуємо"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("Є перерваний тест. Натисни 'Продовжуємо', щоб продовжити.", reply_markup=reply_markup)
            return
    await update.message.reply_text("Обери тест:", reply_markup=reply_markup)

# ------------------ Основний обробник ------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    if user_id not in user_data:
        user_data[user_id] = {
            "stats": {"test1": {"passed":0,"total":0},
                      "test2": {"passed":0,"total":0},
                      "test3": {"passed":0,"total":0}}
        }

    data = user_data[user_id]

    # ------------------ Продовження після паузи ------------------
    if data.get("paused") and text == "Продовжуємо":
        data["paused"] = False
        keyboard = [["Поки що все"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(data["questions"][data["index"]]["question"],
                                        reply_markup=reply_markup)
        save_user_data()
        return

    # ------------------ Кнопка Поки що все ------------------
    if text == "Поки що все" and "questions" in data:
        data["paused"] = True
        keyboard = [["Продовжуємо"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("⏸ Перерва. Коли захочеш, натисни 'Продовжуємо'.",
                                        reply_markup=reply_markup)
        save_user_data()
        return

    # ------------------ Статистика ------------------
    if text == "Статистика":
        stats_text = "\n".join([f"{t.capitalize()}: {v['passed']}/{v['total']}" for t,v in data["stats"].items()])
        await update.message.reply_text(f"📊 Статистика:\n{stats_text}")
        return

    # ------------------ Вибір тесту ------------------
    if text in ["Тест 1","Тест 2","Тест 3"]:
        file = f"test{text[-1]}.txt"
        if not os.path.exists(file):
            await update.message.reply_text(f"Файл {file} не знайдено!")
            return
        questions = load_questions(file)
        random.shuffle(questions)
        data.update({
            "all_questions": questions[:],
            "questions": questions[:],
            "index": 0,
            "score": 0,
            "wrong": [],
            "current_test": text,
            "paused": False,
            "repeat_options": False
        })
        keyboard = [["Поки що все"], ["Статистика"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Починаємо тест!\n\n" + questions[0]["question"],
                                        reply_markup=reply_markup)
        save_user_data()
        return

    # ------------------ Обробка відповіді ------------------
    if "questions" not in data or data["index"] >= len(data["questions"]):
        await update.message.reply_text("Натисни /start і обери тест")
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

    data["index"] += 1

    # ------------------ Наступне питання або завершення ------------------
    if data["index"] < len(questions):
        keyboard = [["Поки що все"], ["Статистика"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(questions[data["index"]]["question"], reply_markup=reply_markup)
    else:
        # Збереження статистики
        key = f"test{data['current_test'][-1]}"
        data["stats"][key]["passed"] += data["score"]
        data["stats"][key]["total"] = len(data["all_questions"])

        await update.message.reply_text(f"🎉 Тест завершено!\nРезультат: {data['score']}/{len(questions)}")

        # Пропозиції дій після завершення
        keyboard = [["Поки що все", "Статистика"]]
        if data["wrong"]:
            keyboard.insert(0, ["Повторити помилки"])
        keyboard.append([t for t in ["Тест 1","Тест 2","Тест 3"] if t != data["current_test"]])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Що хочеш зробити далі?", reply_markup=reply_markup)
        data["repeat_options"] = True
    save_user_data()

# ------------------ Запуск ------------------
if __name__ == "__main__":
    load_user_data()
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
