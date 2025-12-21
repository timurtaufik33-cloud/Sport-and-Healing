
import telebot
from telebot import types
import json, os, threading, time, traceback
from datetime import datetime
import requests

# ================== НАСТРОЙКИ ==================
TOKEN = "8477736982:AAG9P08U2VIYxxOO84Hh_hJhyVj0I1t4RHA"
ADMIN_ID = 123456789
OPENAI_API_KEY = ""   # можно оставить пустым

DATA_FILE = "data.json"
bot = telebot.TeleBot(TOKEN)

# ================== ГОРОДА ==================
CITIES = [
    # 🇰🇿 Казахстан
    "Алматы","Астана","Шымкент","Караганда","Актобе","Тараз","Павлодар",
    "Усть-Каменогорск","Семей","Кызылорда","Атырау","Актау","Кокшетау",
    "Талдыкорган","Жезказган","Рудный","Экибастуз","Темиртау","Туркестан",

    # 🇷🇺 Россия
    "Москва","Санкт-Петербург","Новосибирск","Екатеринбург","Казань",
    "Нижний Новгород","Челябинск","Самара","Омск","Ростов-на-Дону",
    "Уфа","Красноярск","Пермь","Воронеж","Волгоград","Краснодар",
    "Саратов","Тюмень","Тольятти","Ижевск","Барнаул","Иркутск",
    "Хабаровск","Владивосток","Ярославль","Махачкала","Томск","Кемерово"
]

# ================== СПОРТ ==================
SPORTS = {
    "Футбол": ["Руслан Айтбеков", "Алихан Нурланов"],
    "Бокс": ["Арман Султанов", "Жанибек Каримов"],
    "Баскетбол": ["Илья Ковалёв", "Нуржан Сериков"],
    "Волейбол": ["Артём Фролов", "Сергей Малинин"],
    "Плавание": ["Диана Ахметова", "Максат Есимов"],
    "Теннис": ["Александр Рубин", "Ирина Белова"],
    "Настольный теннис": ["Павел Ким", "Олег Сидоров"],
    "Борьба": ["Марат Исламов", "Даурен Сапаров"],
    "Каратэ": ["Рустам Абдуллин", "Азамат Жумабеков"],
    "Таэквондо": ["Канат Беков", "Саян Нуртаев"],
    "Йога": ["Анна Смирнова", "Айгуль Тлеубаева"],
    "Фитнес": ["Ольга Морозова", "Виктор Лапин"],
    "Кроссфит": ["Дмитрий Орлов", "Максим Громов"],
    "Лёгкая атлетика": ["Иван Петров", "Елена Кравцова"],
    "Тяжёлая атлетика": ["Сергей Волков", "Арман Жаксылыков"],
    "Хоккей": ["Андрей Козлов", "Роман Егоров"],
    "Боевые искусства": ["Тимур Рахимов", "Азат Касымов"],
    "Танцы": ["Мария Кузнецова", "Алина Ахметова"]
}

TRAINING_TIME = {
    "morning": "09:00",
    "evening": "18:00"
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

def get_user(uid):
    return db["users"].setdefault(uid, {"stage": "consent"})

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
        "Сменить тренера",
        "Изменить секцию",
        "Изменить город",
        "Удалить мои данные"
    )

# ================== ИИ ==================
def is_question(text):
    return "?" in text or len(text.split()) > 3

def ai_answer(text):
    if not OPENAI_API_KEY:
        return "🤖 Я могу отвечать на любые вопросы о спорте и здоровье."

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Ты фитнес-тренер и консультант по ЗОЖ."},
            {"role": "user", "content": text}
        ]
    }

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=20
    )
    return r.json()["choices"][0]["message"]["content"]

# ================== НАПОМИНАНИЯ ==================
def reminder_loop():
    while True:
        try:
            now = datetime.now()
            for uid, user in db["users"].items():
                if user.get("stage") != "done":
                    continue

                t = TRAINING_TIME.get(user.get("time"))
                if not t:
                    continue

                h, m = map(int, t.split(":"))
                dt = now.replace(hour=h, minute=m, second=0)
                diff = (dt - now).total_seconds()

                if 0 < diff <= 3600:
                    if user.get("last_reminder") == now.strftime("%Y-%m-%d"):
                        continue

                    bot.send_message(
                        uid,
                        f"⏰ Напоминание!\n"
                        f"{user['sport']} сегодня в {t}\n"
                        f"👨‍🏫 {user['trainer']}"
                    )

                    user["last_reminder"] = now.strftime("%Y-%m-%d")
                    save_data()

        except Exception:
            print(traceback.format_exc())

        time.sleep(60)

threading.Thread(target=reminder_loop, daemon=True).start()

# ================== START ==================
@bot.message_handler(commands=["start"])
def start(msg):
    uid = str(msg.chat.id)
    user = get_user(uid)
    user["stage"] = "consent"
    save_data()

    bot.send_message(
        uid,
        "🏋️ FitKazBot\n\n"
        "Для работы нужно согласие на обработку данных.",
        reply_markup=kb("✅ Согласен", "❌ Нет")
    )

# ================== ЛОГИКА ==================
@bot.message_handler(func=lambda m: True)
def handle(msg):
    uid = str(msg.chat.id)
    text = msg.text
    user = get_user(uid)
    stage = user.get("stage")

    try:
        if stage == "consent":
            if text == "✅ Согласен":
                user["stage"] = "name"
                save_data()
                bot.send_message(uid, "Как тебя зовут?")
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
            user["trainer"] = SPORTS[text][0]
            user["stage"] = "time"
            save_data()
            bot.send_message(uid, "Выбери время:", reply_markup=kb("🌅 Утро", "🌙 Вечер"))
            return

        if stage == "time":
            user["time"] = "morning" if text == "🌅 Утро" else "evening"
            user["stage"] = "done"
            save_data()
            bot.send_message(uid, "✅ Ты записан!", reply_markup=main_menu())
            return

        if stage == "change_trainer":
            if text in SPORTS[user["sport"]]:
                user["trainer"] = text
                user["stage"] = "done"
                save_data()
                bot.send_message(uid, "✅ Тренер изменён", reply_markup=main_menu())
            return

        # ===== МЕНЮ =====
        if text == "Сменить тренера":
            user["stage"] = "change_trainer"
            save_data()
            bot.send_message(uid, "Выбери тренера:", reply_markup=kb(*SPORTS[user["sport"]]))
            return

        if text == "Мой профиль":
            bot.send_message(
                uid,
                f"👤 {user['name']}\n"
                f"📞 {user['phone']}\n"
                f"🏙 {user['city']}\n"
                f"🏅 {user['sport']}\n"
                f"🕒 {'Утро' if user['time']=='morning' else 'Вечер'}\n"
                f"👨‍🏫 {user['trainer']}"
            )
            return

        if text == "Моё расписание":
            bot.send_message(uid, f"{user['sport']} — {TRAINING_TIME[user['time']]}")
            return

        if text == "Изменить город":
            user["stage"] = "city"
            save_data()
            bot.send_message(uid, "Выбери город:", reply_markup=kb(*CITIES))
            return

        if text == "Изменить секцию":
            user["stage"] = "sport"
            save_data()
            bot.send_message(uid, "Выбери секцию:", reply_markup=kb(*SPORTS.keys()))
            return

        if text == "Удалить мои данные":
            db["users"].pop(uid, None)
            save_data()
            bot.send_message(uid, "🗑 Данные удалены. Напиши /start")
            return

        if is_question(text):
            bot.send_message(uid, ai_answer(text))
        else:
            bot.send_message(uid, "Выбери пункт меню 👇", reply_markup=main_menu())

    except Exception:
        print(traceback.format_exc())

# ================== RUN ==================
print("FitKazBot улучшенный запущен")
bot.infinity_polling()
