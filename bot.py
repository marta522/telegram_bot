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
DATA_FILE = "user_data.json"  # файл для збереження прогресу
user_data = {}

logging.basicConfig(level=logging.INFO)

# ------------------ Функції для збереження ------------------

def save_user_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)

def load_user_data():
    global user_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            user_data = json.load(f)
            # ключі JSON зберігаються як рядки, треба перетворити на int
            user_data = {int(k): v for k, v in user_data.items()}
    else:
        user_data = {}

# ------------------ Звичайні функції бота ------------------

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

# ------------------ Хендлери ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Тест 1", "Тест 2"], ["Тест 3"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Обери тест:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # ------------------ Завантажуємо користувача при першому виклику ------------------
    if user_id not in user_data:
        user_data[user_id] = {"stats": {}}

    data = user_data[user_id]

    # ------------------ Перерва ------------------
    if data.get("paused"):
        if text == "Продовжуємо":
            data["paused"] = False
            save_user_data()
            keyboard = [["Тест 1", "Тест 2"], ["Тест 3"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("💡 Добре, обери тест, щоб продовжити:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("Тест на паузі. Натисни 'Продовжуємо', щоб повернутися.")
        return

    # ------------------ Вибір тесту ------------------
    if text in ["Тест 1", "Тест 2", "Тест 3"]:
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
            "current_test": text
        })
        data["stats"].setdefault(f"test{text[-1]}", {"passed": 0, "total": len(questions)})
        save_user_data()
        await update.message.reply_text("Починаємо тест!\n\n" + questions[0]["question"])
        return

    # ------------------ Якщо користувач ще не обрав тест ------------------
    if "questions" not in data:
        await update.message.reply_text("Натисни /start і обери тест")
        return

    # ------------------ Обробка кнопок повтору / статистики ------------------
    if data.get("repeat_options"):
        if text == "Пройти тест ще раз":
            data["questions"] = data["all_questions"][:]
            random.shuffle(data["questions"])
            data["index"] = 0
            data["score"] = 0
            data["wrong"] = []
            del data["repeat_options"]
            save_user_data()
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
            save_user_data()
            await update.message.reply_text("Повторюємо тільки помилки!\n\n" + data["questions"][0]["question"])
            return
        elif text == "Статистика":
            stats_msg = ""
            for test_num in range(1, 4):
                key = f"test{test_num}"
                s = data.get("stats", {}).get(key, {"passed": 0, "total": 0})
                stats_msg += f"Тест {test_num}: {s['passed']} з {s['total']}\n"
            await update.message.reply_text(stats_msg)
            return

    # ------------------ Обробка паузи ------------------
    if text == "Поки що все":
        data["paused"] = True
        keyboard = [["Продовжуємо"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        save_user_data()
        await update.message.reply_text("⏸ Перерва. Коли захочеш, натисни 'Продовжуємо'.", reply_markup=reply_markup)
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

    data["index"] += 1
    save_user_data()
    if data["index"] < len(questions):
        await update.message.reply_text(questions[data["index"]]["question"])
    else:
        # Оновлюємо статистику
        key = f"test{data['current_test'][-1]}"
        data["stats"][key]["passed"] += data["score"]
        save_user_data()

        await update.message.reply_text(f"🎉 Тест завершено!\nРезультат: {data['score']}/{len(questions)}")

        keyboard = [["Поки що все", "Статистика"]]
        if data["wrong"]:
            keyboard.insert(0, ["Повторити помилки"])
        keyboard.append([t for t in ["Тест 1","Тест 2","Тест 3"] if t != data["current_test"]])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Що хочеш зробити далі?", reply_markup=reply_markup)
        data["repeat_options"] = True
        save_user_data()

# ------------------ Запуск бота ------------------

if __name__ == "__main__":
    load_user_data()  # завантажуємо прогрес при старті

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
