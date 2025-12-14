
import telebot
from telebot import types
import json, os, threading, time
from datetime import datetime, timedelta
import requests

# ================== НАСТРОЙКИ ==================
TOKEN = "8477736982:AAG9P08U2VIYxxOO84Hh_hJhyVj0I1t4RHA"
ADMIN_ID = 123456789
OPENAI_API_KEY = "8477736982:AAG9P08U2VIYxxOO84Hh_hJhyVj0I1t4RHA"   # можно оставить пустым

DATA_FILE = "data.json"

# ================== БОТ ==================
bot = telebot.TeleBot(TOKEN)

# ================== ДАННЫЕ ==================
CITIES = [
    "Алматы", "Астана", "Шымкент", "Караганда",
    "Актобе", "Тараз", "Павлодар", "Усть-Каменогорск"
]

SPORTS = {
    "Футбол": {
        "trainers": ["Руслан Айтбеков", "Алихан Нурланов"],
        "morning": "09:00",
        "evening": "18:00"
    },
    "Бокс": {
        "trainers": ["Арман Султанов", "Жанибек Каримов"],
        "morning": "08:00",
        "evening": "19:00"
    },
    "Баскетбол": {
        "trainers": ["Илья Ковалёв", "Нуржан Сериков"],
        "morning": "10:00",
        "evening": "17:00"
    },
    "Плавание": {
        "trainers": ["Диана Ахметова", "Максат Есимов"],
        "morning": "07:30",
        "evening": "18:30"
    }
}

TRAINER_CHAT_IDS = {
    "Футбол": ADMIN_ID,
    "Бокс": ADMIN_ID,
    "Баскетбол": ADMIN_ID,
    "Плавание": ADMIN_ID
}

# ================== JSON ==================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_data()

# ================== КНОПКИ ==================
def kb(*args):
    k = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for a in args:
        k.add(a)
    return k

def main_menu():
    return kb(
        "Моё расписание",
        "Мой профиль",
        "Правильное питание",
        "Изменить секцию",
        "Изменить город",
        "Удалить мои данные"
    )

# ================== START ==================
@bot.message_handler(commands=["start"])
def start(msg):
    uid = str(msg.chat.id)
    db["users"].setdefault(uid, {})
    db["users"][uid]["stage"] = "consent"
    save_data()

    bot.send_message(
        uid,
        "🏋‍♂ Привет! Я FitKazBot.\n\n"
        "Я использую твои данные для записи на секции.\n"
        "Ты согласен?",
        reply_markup=kb("✅ Согласен", "❌ Нет")
    )

# ================== ИИ ==================
def ai_answer(question):
    if not OPENAI_API_KEY:
        return "🤖 Я могу отвечать на любые вопросы о спорте и ЗОЖ. ИИ скоро будет подключён!"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Ты фитнес-тренер и консультант по ЗОЖ."},
            {"role": "user", "content": question}
        ]
    }

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data
    )

    return r.json()["choices"][0]["message"]["content"]

# ================== УВЕДОМЛЕНИЕ ТРЕНЕРУ ==================
def notify_trainer(user):
    trainer_id = TRAINER_CHAT_IDS.get(user["sport"])
    if not trainer_id:
        return

    bot.send_message(
        trainer_id,
        f"📢 Новый спортсмен\n\n"
        f"👤 {user['name']}\n"
        f"🏙 {user['city']}\n"
        f"🏅 {user['sport']}\n"
        f"🕒 {user['time']}\n"
        f"📞 {user['phone']}"
    )

# ================== НАПОМИНАНИЯ ==================
def reminder_loop():
    while True:
        try:
            now = datetime.now()

            for uid, user in db["users"].items():

                # ❗ 1. Проверяем, что пользователь полностью зарегистрирован
                if user.get("stage") != "done":
                    continue

                sport = user.get("sport")
                time_type = user.get("time")

                # ❗ 2. Если нет спорта или времени — пропускаем
                if not sport or not time_type:
                    continue

                if sport not in SPORTS:
                    continue

                if time_type not in SPORTS[sport]:
                    continue

                training_time = SPORTS[sport][time_type]
                h, m = map(int, training_time.split(":"))

                training_dt = now.replace(hour=h, minute=m, second=0)

                # ❗ 3. Проверка «за 1 час»
                diff = (training_dt - now).total_seconds()

                if 0 < diff <= 3600:
                    today = now.strftime("%Y-%m-%d")

                    if user.get("last_reminder") == today:
                        continue

                    bot.send_message(
                        uid,
                        f"⏰ Напоминание!\n\n"
                        f"Сегодня тренировка 🏋\n"
                        f"🏅 {sport}\n"
                        f"🕒 В {training_time}\n"
                        f"👨‍🏫 {user.get('trainer', 'Тренер')}"
                    )

                    user["last_reminder"] = today
                    save_data()

        except Exception as e:
            print("Ошибка в reminder_loop:", e)

        time.sleep(60)


# ================== ОСНОВНАЯ ЛОГИКА ==================
@bot.message_handler(func=lambda m: True)
def handle(msg):
    uid = str(msg.chat.id)
    text = msg.text
    user = db["users"].get(uid, {})
    stage = user.get("stage")

    if stage == "consent":
        if text == "✅ Согласен":
            user["stage"] = "name"
            save_data()
            bot.send_message(uid, "Как тебя зовут?")
        else:
            bot.send_message(uid, "Без согласия я не могу работать.")
        return

    if stage == "name":
        user["name"] = text
        user["stage"] = "phone"
        save_data()
        bot.send_message(uid, "Введите номер телефона:")
        return

    if stage == "phone":
        user["phone"] = text
        user["stage"] = "city"
        save_data()
        bot.send_message(uid, "Выбери город:", reply_markup=kb(*CITIES))
        return

    if stage == "city":
        user["city"] = text
        user["stage"] = "sport"
        save_data()
        bot.send_message(uid, "Выбери секцию:", reply_markup=kb(*SPORTS.keys()))
        return

    if stage == "sport":
        user["sport"] = text
        user["trainer"] = SPORTS[text]["trainers"][0]
        user["stage"] = "time"
        save_data()
        bot.send_message(uid, "Выбери время:", reply_markup=kb("morning", "evening"))
        return

    if stage == "time":
        user["time"] = text
        user["stage"] = "done"
        save_data()
        notify_trainer(user)
        bot.send_message(uid, "✅ Ты записан!", reply_markup=main_menu())
        return

    # ===== МЕНЮ =====
    if text == "Мой профиль":
        bot.send_message(
            uid,
            f"👤 {user['name']}\n"
            f"📞 {user['phone']}\n"
            f"🏙 {user['city']}\n"
            f"🏅 {user['sport']}\n"
            f"🕒 {user['time']}"
        )
        return

    if text == "Моё расписание":
        bot.send_message(
            uid,
            f"📅 Расписание:\n"
            f"{user['sport']} — {SPORTS[user['sport']][user['time']]}"
        )
        return

    if text == "Правильное питание":
        bot.send_message(uid, ai_answer("Правильное питание для спортсмена"))
        return

    if text == "Изменить город":
        user["stage"] = "city"
        save_data()
        bot.send_message(uid, "Выбери новый город:", reply_markup=kb(*CITIES))
        return

    if text == "Изменить секцию":
        user["stage"] = "sport"
        save_data()
        bot.send_message(uid, "Выбери секцию:", reply_markup=kb(*SPORTS.keys()))
        return

    if text == "Удалить мои данные":
        db["users"].pop(uid)
        save_data()
        bot.send_message(uid, "🗑 Данные удалены.")
        return

    # ===== ИИ НА ВСЁ ОСТАЛЬНОЕ =====
    bot.send_message(uid, ai_answer(text))

# ================== ЗАПУСК ==================
print("FitKazBot запущен")
bot.infinity_polling()