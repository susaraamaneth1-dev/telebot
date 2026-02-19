import telebot
import sqlite3
import threading
import time
import os
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

# ================= CONFIG ================= #

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8540477830

BANK_DETAILS = """
🏦 Bank Details

Bank: Commercial Bank
Account Name: Study Master
Account Number: 1234567890
Branch: Colombo
"""

bot = telebot.TeleBot(TOKEN)

# ================= DATABASE ================= #

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

# ================= RESET COMMAND ================= #

@bot.message_handler(commands=['resetme'])
def reset_profile(message):

    chat_id = message.chat.id

    cursor.execute("DELETE FROM students WHERE telegram_id=?", (chat_id,))
    conn.commit()

    if chat_id in user_data:
        del user_data[chat_id]

    bot.send_message(chat_id, "🔄 Your profile has been reset.\nLet's register again.")

    msg = bot.send_message(chat_id, "Enter Student Name:")
    bot.register_next_step_handler(msg, get_grade)


# ================= START ================= #

@bot.message_handler(commands=['start'])
def start(message):

    chat_id = message.chat.id

    if chat_id == ADMIN_ID:
        bot.send_message(chat_id,
            "🛠 Admin Mode Ready.\nApprove using:\n/approve_USERID https://notionlink")
        return

    cursor.execute("SELECT status,expiry_date,notion_link FROM students WHERE telegram_id=?", (chat_id,))
    row = cursor.fetchone()

    if row and row[0] == "approved":

        expiry_date = datetime.strptime(row[1], "%Y-%m-%d")
        remaining = (expiry_date - datetime.now()).days

        if remaining <= 0:
            bot.send_message(chat_id, "⚠️ Your plan expired.")
            return

        bot.send_message(chat_id, f"""
🎓 STUDENT DASHBOARD

🚀 Start Project:
{row[2]}

⏳ Days Remaining: {remaining}
""")
        return

    msg = bot.send_message(chat_id, "Enter Student Name:")
    bot.register_next_step_handler(msg, get_grade)


# ================= REGISTRATION ================= #

def get_grade(message):
    user_data[message.chat.id] = {"name": message.text}
    msg = bot.send_message(message.chat.id, "Enter Grade:")
    bot.register_next_step_handler(msg, get_exam)

def get_exam(message):
    user_data[message.chat.id]["grade"] = message.text
    msg = bot.send_message(message.chat.id, "O/L or A/L + Exam Year:")
    bot.register_next_step_handler(msg, get_subjects)

def get_subjects(message):
    user_data[message.chat.id]["exam_info"] = message.text
    msg = bot.send_message(message.chat.id, "Enter Subjects:")
    bot.register_next_step_handler(msg, get_parent)

def get_parent(message):
    user_data[message.chat.id]["subjects"] = message.text
    msg = bot.send_message(message.chat.id, "Enter Parent Phone:")
    bot.register_next_step_handler(msg, get_schedule)

def get_schedule(message):
    user_data[message.chat.id]["parent_phone"] = message.text
    msg = bot.send_message(message.chat.id, "Enter Weekly Schedule:")
    bot.register_next_step_handler(msg, get_plan)

def get_plan(message):
    user_data[message.chat.id]["weekly_schedule"] = message.text

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("2 Week - 300 LKR")
    kb.add("1 Month - 700 LKR")

    msg = bot.send_message(message.chat.id, "Select Plan:", reply_markup=kb)
    bot.register_next_step_handler(msg, get_target)

def get_target(message):

    chat_id = message.chat.id

    if "2 Week" in message.text:
        plan = "2 Week"
    else:
        plan = "1 Month"

    user_data[chat_id]["plan"] = plan

    msg = bot.send_message(chat_id,
        "Your Target? (Type None if no target)",
        reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, finish_registration)

def finish_registration(message):

    chat_id = message.chat.id
    user_data[chat_id]["target"] = message.text

    bot.send_message(chat_id, BANK_DETAILS)

    msg = bot.send_message(chat_id, "Upload Payment Receipt:")
    bot.register_next_step_handler(msg, save_receipt)


# ================= RECEIPT ================= #

def save_receipt(message):

    if not message.photo:
        bot.send_message(message.chat.id, "Please upload image.")
        return

    chat_id = message.chat.id
    file_id = message.photo[-1].file_id
    data = user_data[chat_id]

    cursor.execute("""
    INSERT OR REPLACE INTO students
    (telegram_id,name,grade,exam_info,subjects,parent_phone,weekly_schedule,plan,target,status,receipt_file_id)
    VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (chat_id,data["name"],data["grade"],data["exam_info"],
          data["subjects"],data["parent_phone"],data["weekly_schedule"],
          data["plan"],data["target"],"pending",file_id))
    conn.commit()

    bot.send_message(chat_id, "✅ Waiting for Admin Approval.")

    summary = f"""
📌 NEW STUDENT

👤 Name: {data['name']}
🎓 Grade: {data['grade']}
📚 Exam: {data['exam_info']}
📖 Subjects: {data['subjects']}
📞 Parent: {data['parent_phone']}
🗓 Schedule: {data['weekly_schedule']}
💰 Plan: {data['plan']}
🎯 Target: {data['target']}

Approve using:
/approve_{chat_id} https://notionlink
"""

    bot.send_photo(ADMIN_ID, file_id, caption=summary)


# ================= APPROVE ================= #

@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.text.startswith("/approve_"))
def approve(message):

    try:
        parts = message.text.split()

        if len(parts) < 2:
            bot.send_message(ADMIN_ID,
                "❌ Format:\n/approve_USERID https://notionlink")
            return

        tg_id = int(parts[0].split("_")[1])
        link = parts[1]

        cursor.execute("SELECT plan FROM students WHERE telegram_id=?", (tg_id,))
        row = cursor.fetchone()

        if not row:
            bot.send_message(ADMIN_ID, "❌ Student not found.")
            return

        duration = 14 if row[0] == "2 Week" else 30

        join_date = datetime.now()
        expiry_date = join_date + timedelta(days=duration)

        cursor.execute("""
        UPDATE students
        SET status='approved',
            join_date=?,
            expiry_date=?,
            notion_link=?
        WHERE telegram_id=?
        """, (join_date.strftime("%Y-%m-%d"),
              expiry_date.strftime("%Y-%m-%d"),
              link,
              tg_id))
        conn.commit()

        bot.send_message(tg_id, f"""
🎉 Payment Approved!

🚀 Start Project:
{link}

📅 Start: {join_date.strftime("%Y-%m-%d")}
⏳ Expire: {expiry_date.strftime("%Y-%m-%d")}
""")

        bot.send_message(ADMIN_ID, "✅ Student Approved.")

    except Exception as e:
        bot.send_message(ADMIN_ID, f"Error: {e}")


# ================= EXPIRE CHECK ================= #

def daily_check():
    while True:

        cursor.execute("SELECT telegram_id,expiry_date FROM students WHERE status='approved'")
        rows = cursor.fetchall()

        for tg_id, expiry in rows:
            expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
            if datetime.now() >= expiry_date:
                cursor.execute("UPDATE students SET status='expired' WHERE telegram_id=?", (tg_id,))
                conn.commit()
                bot.send_message(tg_id, "⚠️ Your plan expired.")
                bot.send_message(ADMIN_ID, f"Student {tg_id} expired.")

        time.sleep(86400)

threading.Thread(target=daily_check).start()

print("🔥 FINAL PREMIUM BOT RUNNING...")

while True:
    try:
        bot.infinity_polling()
    except:
        time.sleep(5)
