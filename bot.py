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
user_data = {}  # Ключ: user_id, значення: прогрес по кожному тесту
logging.basicConfig(level=logging.INFO)

TESTS = ["Тест 1", "Тест 2", "Тест 3"]

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

def get_keyboard(user_id, current_test=None, paused=False):
    keyboard = []
    
    if not paused:  # Під час тесту
        for t in TESTS:
            if t != current_test:
                keyboard.append([t])
        keyboard.append(["Статистика", "Поки що все"])
    else:  # Після натискання «Поки що все»
        keyboard.append(["Продовжуємо"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ------------------ Команди ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {}
    await update.message.reply_text("Обери тест:", reply_markup=get_keyboard(user_id))

# ------------------ Обробка повідомлень ------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_data:
        user_data[user_id] = {}

    # ------------------ Статистика ------------------
    if text == "Статистика":
        stats = []
        for t in TESTS:
            if t in user_data[user_id]:
                data = user_data[user_id][t]
                done = data["index"]
                total = len(data["questions"])
                stats.append(f"{t}: {done} з {total}")
            else:
                stats.append(f"{t}: 0 з ?")
        await update.message.reply_text("\n".join(stats))
        return

    # ------------------ Продовження після паузи ------------------
    if text == "Продовжуємо":
        for t in TESTS:
            if t in user_data[user_id] and user_data[user_id][t].get("paused"):
                data = user_data[user_id][t]
                data["paused"] = False
                await update.message.reply_text("Продовжуємо тест!\n\n" + data["questions"][data["index"]]["question"],
                                                reply_markup=get_keyboard(user_id, current_test=t))
                return
        await update.message.reply_text("Немає тесту для продовження.")
        return

    # ------------------ Вибір тесту ------------------
    if text in TESTS:
        current_test = text
        if current_test not in user_data[user_id]:
            # Завантажуємо питання
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
        await update.message.reply_text(data["questions"][data["index"]]["question"],
                                        reply_markup=get_keyboard(user_id, current_test=current_test))
        return

    # ------------------ Поки що все ------------------
    if text == "Поки що все":
        for t in TESTS:
            if t in user_data[user_id] and not user_data[user_id][t].get("paused"):
                user_data[user_id][t]["paused"] = True
                await update.message.reply_text("Тест призупинено. Можна продовжити пізніше.",
                                                reply_markup=get_keyboard(user_id, paused=True))
                return
        await update.message.reply_text("Немає активного тесту для паузи.")
        return

    # ------------------ Обробка відповіді ------------------
    # Визначаємо активний тест (не paused)
    current_test = None
    for t in TESTS:
        if t in user_data[user_id] and not user_data[user_id][t].get("paused"):
            current_test = t
            break

    if current_test is None:
        await update.message.reply_text("Немає активного тесту. Оберіть тест або продовжте його.")
        return

    data = user_data[user_id][current_test]
    current_index = data["index"]
    questions = data["questions"]
    correct = questions[current_index]["answer"]

    if text.upper() == correct:
        data["score"] += 1
        await update.message.reply_text("✅ Правильно!")
    else:
        await update.message.reply_text(f"❌ Неправильно! Правильна відповідь: {correct}")
        data["wrong"].append(questions[current_index])

    data["index"] += 1
    if data["index"] < len(questions):
        await update.message.reply_text(questions[data["index"]]["question"],
                                        reply_markup=get_keyboard(user_id, current_test=current_test))
    else:
        # Тест завершено
        await update.message.reply_text(f"🎉 Тест {current_test} завершено!\nРезультат: {data['score']}/{len(questions)}")
        keyboard = [["Пройти тест ще раз"]]
        if data["wrong"]:
            keyboard.insert(0, ["Повторити помилки"])
        reply_markup = ReplyKeyboardMarkup(keyboard + [[t for t in TESTS if t != current_test]], resize_keyboard=True)
        await update.message.reply_text("Що робимо далі?", reply_markup=reply_markup)
        data["paused"] = True  # Завершений тест можна повторити пізніше

# ------------------ Запуск webhook ------------------

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
