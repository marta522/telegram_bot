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

logging.basicConfig(level=logging.INFO)

# Зберігаємо дані користувачів
user_data = {}

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

def build_test_keyboard(current_test=None):
    # Завжди доступні кнопки «Поки що все» і «Статистика»
    keyboard = [["Поки що все"], ["Статистика"]]
    # Додаємо інші тести, крім поточного
    for test in ["Тест 1", "Тест 2", "Тест 3"]:
        if test != current_test:
            keyboard.append([test])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data.pop(user_id, None)
    keyboard = [["Тест 1", "Тест 2"], ["Тест 3"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Обери тест:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # ------------------ Якщо користувач на паузі ------------------
    if user_id in user_data and user_data[user_id].get("paused"):
        if text == "Продовжуємо":
            user_data[user_id]["paused"] = False
            data = user_data[user_id]
            index = data["index"]
            await update.message.reply_text(
                data["questions"][index]["question"],
                reply_markup=build_test_keyboard(current_test=data["current_test"])
            )
            return
        elif text in ["Тест 1", "Тест 2", "Тест 3"]:
            # Обирає інший тест
            await start_test(update, text)
            return
        elif text == "Статистика":
            await show_statistics(update, user_id)
            return
        else:
            await update.message.reply_text("Натисни кнопку для дії.")
            return

    # ------------------ Статистика ------------------
    if text == "Статистика":
        await show_statistics(update, user_id)
        return

    # ------------------ Пауза ------------------
    if text == "Поки що все":
        if user_id not in user_data:
            await update.message.reply_text("Ще не обрано тест. Натисни /start")
            return
        user_data[user_id]["paused"] = True
        await update.message.reply_text(
            "Тест призупинено. Коли захочеш продовжити – натисни кнопку «Продовжуємо».",
            reply_markup=ReplyKeyboardMarkup([["Продовжуємо"]], resize_keyboard=True)
        )
        return

    # ------------------ Вибір тесту ------------------
    if text in ["Тест 1", "Тест 2", "Тест 3"]:
        await start_test(update, text)
        return

    # ------------------ Якщо тест ще не обраний ------------------
    if user_id not in user_data or "questions" not in user_data[user_id]:
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

    data["index"] += 1

    if data["index"] < len(questions):
        await update.message.reply_text(
            questions[data["index"]]["question"],
            reply_markup=build_test_keyboard(current_test=data["current_test"])
        )
    else:
        # ------------------ Завершення тесту ------------------
        all_q = len(data["questions"])
        score = data["score"]
        # Запам’ятовуємо статистику
        if "stats" not in user_data[user_id]:
            user_data[user_id]["stats"] = {}
        user_data[user_id]["stats"][data["current_test"]] = f"{score} з {all_q}"

        # Пропонуємо повторити або інші дії
        keyboard = [["Пройти тест ще раз"]]
        if data["wrong"]:
            keyboard.insert(0, ["Повторити помилки"])
        # Додаємо інші тести
        for test in ["Тест 1", "Тест 2", "Тест 3"]:
            if test != data["current_test"]:
                keyboard.append([test])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"🎉 Тест завершено!\nРезультат: {score}/{all_q}\nЩо хочеш зробити далі?",
            reply_markup=reply_markup
        )
        # Маркер повторного вибору
        data["repeat_options"] = True

# ------------------ Додаткові функції ------------------

async def start_test(update: Update, text: str):
    user_id = update.effective_user.id
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
        "current_test": text,
        "paused": False
    }
    await update.message.reply_text(
        "Починаємо тест!\n\n" + questions[0]["question"],
        reply_markup=build_test_keyboard(current_test=text)
    )

async def show_statistics(update: Update, user_id):
    stats = user_data.get(user_id, {}).get("stats", {})
    msg = "📊 Статистика:\n"
    for test in ["Тест 1", "Тест 2", "Тест 3"]:
        msg += f"{test}: {stats.get(test, '0 з 0')}\n"
    await update.message.reply_text(msg)

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
