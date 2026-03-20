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
user_data = {}
STATS_FILE = "stats.json"
logging.basicConfig(level=logging.INFO)

# ------------------ Робота зі статистикою ------------------
def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

stats = load_stats()

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

    # ------------------ Обробка кнопки "Статистика" ------------------
    if text == "Статистика":
        user_stats = stats.get(str(user_id), {})
        output = []
        for i in range(1, 4):
            done = user_stats.get(f"test{i}_done", 0)
            total = user_stats.get(f"test{i}_all", 0)
            output.append(f"Тест{i}: {done} з {total}")
        await update.message.reply_text("\n".join(output))
        return

    # ------------------ Обробка кнопки "Поки що все" або "Продовжити" ------------------
    if user_id in user_data and "pause" in user_data[user_id]:
        data = user_data[user_id]
        if text == "Продовжити":
            keyboard = [["Тест 1", "Тест 2"], ["Тест 3"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            del data["pause"]
            await update.message.reply_text("Обери тест:", reply_markup=reply_markup)
            return
        else:
            await update.message.reply_text("Натисни 'Продовжити', коли будеш готовий.")
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
            "test_number": text[-1]
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
        await update.message.reply_text(questions[data["index"]]["question"])
    else:
        # ------------------ Оновлюємо статистику ------------------
        user_stats = stats.get(str(user_id), {})
        key_done = f"test{data['test_number']}_done"
        prev_done = user_stats.get(key_done, 0)
        # Запам'ятовуємо максимальну кількість правильних відповідей
        user_stats[key_done] = max(prev_done, data["score"])
        user_stats[f"test{data['test_number']}_all"] = len(data["all_questions"])
        stats[str(user_id)] = user_stats
        save_stats(stats)

        await update.message.reply_text(f"🎉 Тест завершено!\nРезультат: {data['score']}/{len(questions)}")

        # ------------------ Пропонуємо дії після тесту ------------------
        keyboard = []
        if data["wrong"]:
            keyboard.append(["Повторити помилки"])
        keyboard.append(["Пройти тест ще раз"])
        for i in range(1, 4):
            if str(i) != data["test_number"]:
                keyboard.append([f"Тест {i}"])
        keyboard.append(["Статистика"])
        keyboard.append(["Поки що все"])
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
