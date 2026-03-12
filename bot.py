import os
import time
import sqlite3
import threading
from datetime import datetime, timedelta

import telebot
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8540477830

if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is missing.")

BANK_DETAILS = """
🏦 Bank Details

Bank: PEOPLE'S BANK
Account Name: SUSARA AMANETH KOKU HENNEDIGE
Account Number: 278-2-001-0-0097988
Branch: Nittambuwa
"""

WELCOME_MESSAGE = """
🌱 EduGrow වෙත ඔබව සාදරයෙන් පිළිගනිමු

ඔබගේ අධ්‍යයන කාලය නිවැරදිව සැලසුම් කර
දෛනික සාර්ථකත්වයට මග පෙන්වීම අපගේ අරමුණයි.

ඒ සඳහා පහත විස්තර bot හට එවන්න.

📌 අවශ්‍ය විස්තර

⏺️ ඔබගේ නම

⏺️ ඉගෙනු ලබන ශ්‍රේණිය

⏺️ O/L හෝ A/L + Exam Year

⏺️ අධ්‍යයනය කරන විෂයන්

උදාහරණයක් ලෙස:

1️⃣ සිංහල
2️⃣ ගණිතය
3️⃣ ඉංග්‍රීසි

📌 Weekly Schedule

ඔබගේ සතියේ කාල ව්‍යාප්තිය මෙලෙස එවන්න.

උදාහරණය:

සදුදා

1️⃣ පාසල් කාලය
(පාසලට සූදානම් වන මොහොත සිට
නිවසට පැමිණෙන වෙලාව දක්වා)

Ex:
5.30 AM - 2.00 PM

2️⃣ උපකාරක පන්ති කාලය
(පවතිනවානම් පමණක්)

Ex:
4.00 PM - 6.00 PM

📌 මෙලෙස සතියේ දවස් 7 සඳහාම පැහැදිලිව එවන්න.

🎯 Target

ඔබ මෙම කාලය තුල බලාපොරොත්තු වන ප්‍රතිඵලය එවන්න.

උදාහරණ:
• Maths – A pass
• Science – Improve marks

විශේෂ target නොමැති නම්
none
ලෙස type කරන්න.

⚠️ වැදගත්

ඔබට ලැබෙන ID අංකය භාවිතා කර
කිසිදු දිනක plan එක අතපසු වුවහොත්
අදාළ දිනය සහ කාලය සඳහන් කර
Discuss Group තුළ එවන්න.

❓ ගැටළු ඇත්නම්

Discuss Group හරහා හෝ
📥 WhatsApp: 0769810615

වෙත යොමු කරන්න.

EduGrow
Build • Discipline • Rise
"""

# මෙතන ඔයාගේ bot username එක දාන්න
BOT_USERNAME = "@WORLDSTUDYGROWBOT"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= DATABASE =================

conn = sqlite3.connect("students_final.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    telegram_id INTEGER PRIMARY KEY,
    name TEXT,
    grade TEXT,
    exam_info TEXT,
    subjects TEXT,
    parent_phone TEXT,
    weekly_schedule TEXT,
    plan TEXT,
    target TEXT,
    status TEXT,
    join_date TEXT,
    expiry_date TEXT,
    receipt_file_id TEXT,
    notion_link TEXT
)
""")
conn.commit()

user_data = {}

# ================= HELPERS =================

def send_registration_intro(chat_id):
    bot.send_message(chat_id, WELCOME_MESSAGE)
    msg = bot.send_message(chat_id, "👤 ඔබගේ නම type කරන්න:")
    bot.register_next_step_handler(msg, get_name)

def get_remaining_days(expiry_date_str):
    expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
    remaining = (expiry_date - datetime.now()).days
    return remaining

# ================= RESET COMMAND =================

@bot.message_handler(commands=['resetme'])
def reset_profile(message):
    chat_id = message.chat.id

    cursor.execute("DELETE FROM students WHERE telegram_id=?", (chat_id,))
    conn.commit()

    if chat_id in user_data:
        del user_data[chat_id]

    bot.send_message(chat_id, "🔄 ඔබගේ profile එක reset කරලා තියෙනවා.\nඅපි ආයෙ මුල ඉඳන් register වෙමු.")
    send_registration_intro(chat_id)

# ================= GROUP WELCOME =================

@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    for user in message.new_chat_members:
        name = user.first_name if user.first_name else "Student"

        if user.username:
            mention = f"@{user.username}"
        else:
            mention = name

        welcome_text = f"""
🌱 Welcome {mention} to EduGrow!

ඔබගේ study journey එක organize කරගන්න
අපගේ EduGrow Bot එකට connect වෙන්න.

🤖 https://t.me/{BOT_USERNAME}?start=welcome

Build • Discipline • Rise
"""
        bot.send_message(message.chat.id, welcome_text)

# ================= START =================

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    text = message.text or ""

    if chat_id == ADMIN_ID:
        bot.send_message(
            chat_id,
            "🛠 Admin Mode Ready.\n\nApprove using:\n<code>/approve_USERID https://notionlink</code>"
        )
        return

    if text.startswith("/start welcome"):
        send_registration_intro(chat_id)
        return

    cursor.execute("SELECT status, expiry_date, notion_link FROM students WHERE telegram_id=?", (chat_id,))
    row = cursor.fetchone()

    if row and row[0] == "approved":
        remaining = get_remaining_days(row[1])

        if remaining <= 0:
            bot.send_message(chat_id, "⚠️ ඔබගේ plan එක expire වෙලා තියෙනවා.")
            return

        bot.send_message(chat_id, f"""
🎓 <b>STUDENT DASHBOARD</b>

🚀 <b>Start Project:</b>
{row[2]}

⏳ <b>Days Remaining:</b> {remaining}
""")
        return

    send_registration_intro(chat_id)

# ================= REGISTRATION =================

def get_name(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text.strip()}

    msg = bot.send_message(chat_id, "🎓 ඉගෙනු ලබන ශ්‍රේණිය type කරන්න:")
    bot.register_next_step_handler(msg, get_grade)

def get_grade(message):
    chat_id = message.chat.id
    user_data[chat_id]["grade"] = message.text.strip()

    msg = bot.send_message(chat_id, "📚 O/L හෝ A/L + Exam Year type කරන්න:\n\nExample: A/L 2027")
    bot.register_next_step_handler(msg, get_exam)

def get_exam(message):
    chat_id = message.chat.id
    user_data[chat_id]["exam_info"] = message.text.strip()

    msg = bot.send_message(chat_id, "📖 ඔබ අධ්‍යයනය කරන විෂයන් type කරන්න:")
    bot.register_next_step_handler(msg, get_subjects)

def get_subjects(message):
    chat_id = message.chat.id
    user_data[chat_id]["subjects"] = message.text.strip()

    msg = bot.send_message(chat_id, "📞 Parent Phone number එක type කරන්න:")
    bot.register_next_step_handler(msg, get_parent)

def get_parent(message):
    chat_id = message.chat.id
    user_data[chat_id]["parent_phone"] = message.text.strip()

    msg = bot.send_message(
        chat_id,
        "🗓 ඔබගේ Weekly Schedule type කරන්න.\n\n"
        "Example:\n"
        "සදුදා\n"
        "1. පාසල් කාලය - 5.30 AM - 2.00 PM\n"
        "2. පන්ති කාලය - 4.00 PM - 6.00 PM\n\n"
        "මෙලෙස සතියේ දවස් 7ම type කරන්න."
    )
    bot.register_next_step_handler(msg, get_schedule)

def get_schedule(message):
    chat_id = message.chat.id
    user_data[chat_id]["weekly_schedule"] = message.text.strip()

    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("5 Days Free Trial")
    kb.add("2 Week - 300 LKR")
    kb.add("1 Month - 700 LKR")

    msg = bot.send_message(chat_id, "💰 Plan එක select කරන්න:", reply_markup=kb)
    bot.register_next_step_handler(msg, get_plan)

def get_plan(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if "5 Days" in text:
        plan = "5 Days Free Trial"
    elif "2 Week" in text:
        plan = "2 Week"
    elif "1 Month" in text:
        plan = "1 Month"
    else:
        msg = bot.send_message(chat_id, "⚠️ කරුණාකර valid plan එකක් select කරන්න.")
        bot.register_next_step_handler(msg, get_plan)
        return

    user_data[chat_id]["plan"] = plan

    msg = bot.send_message(
        chat_id,
        "🎯 ඔබගේ target එක type කරන්න.\n\nවිශේෂ target නැත්නම් <b>none</b> ලෙස type කරන්න.",
        reply_markup=ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, finish_registration)

def finish_registration(message):
    chat_id = message.chat.id
    user_data[chat_id]["target"] = message.text.strip()

    bot.send_message(chat_id, BANK_DETAILS)

    msg = bot.send_message(chat_id, "📷 Payment Receipt image එක upload කරන්න:")
    bot.register_next_step_handler(msg, save_receipt)

# ================= RECEIPT =================

def save_receipt(message):
    chat_id = message.chat.id

    if not message.photo:
        msg = bot.send_message(chat_id, "⚠️ කරුණාකර receipt image එකක් upload කරන්න.")
        bot.register_next_step_handler(msg, save_receipt)
        return

    file_id = message.photo[-1].file_id
    data = user_data.get(chat_id)

    if not data:
        bot.send_message(chat_id, "⚠️ Session expired. කරුණාකර /start ගහලා ආයෙ පටන් ගන්න.")
        return

    cursor.execute("""
    INSERT OR REPLACE INTO students
    (telegram_id, name, grade, exam_info, subjects, parent_phone, weekly_schedule, plan, target, status, receipt_file_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        chat_id,
        data["name"],
        data["grade"],
        data["exam_info"],
        data["subjects"],
        data["parent_phone"],
        data["weekly_schedule"],
        data["plan"],
        data["target"],
        "pending",
        file_id
    ))
    conn.commit()

    bot.send_message(chat_id, "✅ ඔබගේ විස්තර සහ receipt එක ලැබී ඇත.\nදැන් Admin Approval සඳහා බලා සිටින්න.")

    summary = f"""
📌 <b>NEW STUDENT</b>

👤 <b>Name:</b> {data['name']}
🎓 <b>Grade:</b> {data['grade']}
📚 <b>Exam:</b> {data['exam_info']}
📖 <b>Subjects:</b> {data['subjects']}
📞 <b>Parent:</b> {data['parent_phone']}
🗓 <b>Schedule:</b> {data['weekly_schedule']}
💰 <b>Plan:</b> {data['plan']}
🎯 <b>Target:</b> {data['target']}

Approve using:
<code>/approve_{chat_id} https://notionlink</code>
"""

    bot.send_photo(ADMIN_ID, file_id, caption=summary)

    if chat_id in user_data:
        del user_data[chat_id]

# ================= APPROVE =================

@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.text and m.text.startswith("/approve_"))
def approve(message):
    try:
        parts = message.text.split()

        if len(parts) < 2:
            bot.send_message(
                ADMIN_ID,
                "❌ Format:\n<code>/approve_USERID https://notionlink</code>"
            )
            return

        tg_id = int(parts[0].split("_")[1])
        link = parts[1]

        cursor.execute("SELECT plan FROM students WHERE telegram_id=?", (tg_id,))
        row = cursor.fetchone()

        if not row:
            bot.send_message(ADMIN_ID, "❌ Student not found.")
            return

        if row[0] == "5 Days Free Trial":
            duration = 5
        elif row[0] == "2 Week":
            duration = 14
        else:
            duration = 30

        join_date = datetime.now()
        expiry_date = join_date + timedelta(days=duration)

        cursor.execute("""
        UPDATE students
        SET status='approved',
            join_date=?,
            expiry_date=?,
            notion_link=?
        WHERE telegram_id=?
        """, (
            join_date.strftime("%Y-%m-%d"),
            expiry_date.strftime("%Y-%m-%d"),
            link,
            tg_id
        ))
        conn.commit()

        bot.send_message(tg_id, f"""
🎉 <b>Payment Approved!</b>

🚀 <b>Start Project:</b>
{link}

📅 <b>Start:</b> {join_date.strftime("%Y-%m-%d")}
⏳ <b>Expire:</b> {expiry_date.strftime("%Y-%m-%d")}
""")

        bot.send_message(ADMIN_ID, "✅ Student Approved.")

    except Exception as e:
        bot.send_message(ADMIN_ID, f"Error: {e}")

# ================= DAILY EXPIRE CHECK =================

def daily_check():
    while True:
        try:
            cursor.execute("SELECT telegram_id, expiry_date FROM students WHERE status='approved'")
            rows = cursor.fetchall()

            for tg_id, expiry in rows:
                expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
                if datetime.now() >= expiry_date:
                    cursor.execute("UPDATE students SET status='expired' WHERE telegram_id=?", (tg_id,))
                    conn.commit()
                    bot.send_message(tg_id, "⚠️ ඔබගේ plan එක expire වෙලා තියෙනවා.")
                    bot.send_message(ADMIN_ID, f"Student {tg_id} expired.")
        except Exception as e:
            print("Expire check error:", e)

        time.sleep(86400)

threading.Thread(target=daily_check, daemon=True).start()

print("🔥 FINAL PREMIUM BOT RUNNING...")

bot.infinity_polling(skip_pending=True)
