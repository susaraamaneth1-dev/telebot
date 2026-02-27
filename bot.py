import telebot
import sqlite3
import threading
import time
import os
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8540477830

BANK_DETAILS = """
🏦 Bank Details

Bank: Commercial Bank
Account Name: Study Master
Account Number: 1234567890
Branch: Colombo
"""

bot = telebot.TeleBot(TOKEN)

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
notion_link TEXT,
last_confirm TEXT
)
""")
conn.commit()

user_data = {}

# ================= RESET =================

@bot.message_handler(commands=['resetme'])
def reset_profile(message):
    chat_id = message.chat.id
    cursor.execute("DELETE FROM students WHERE telegram_id=?", (chat_id,))
    conn.commit()

    if chat_id in user_data:
        del user_data[chat_id]

    bot.send_message(chat_id, "🔄 Profile reset. Register again.")
    msg = bot.send_message(chat_id, "Enter Student Name:")
    bot.register_next_step_handler(msg, get_grade)

# ================= START =================

@bot.message_handler(commands=['start'])
def start(message):

    chat_id = message.chat.id

    if chat_id == ADMIN_ID:
        bot.send_message(chat_id,
            "🛠 Admin Mode\n"
            "/approve_USERID link\n"
            "/dailycheck\n"
            "/todayreport")
        return

    cursor.execute("SELECT status,expiry_date,notion_link FROM students WHERE telegram_id=?", (chat_id,))
    row = cursor.fetchone()

    if row and row[0] == "approved":
        expiry_date = datetime.strptime(row[1], "%Y-%m-%d")
        remaining = (expiry_date - datetime.now()).days

        if remaining <= 0:
            bot.send_message(chat_id, "⚠️ Plan expired.")
            return

        bot.send_message(chat_id,
            f"🎓 DASHBOARD\n\n"
            f"🚀 {row[2]}\n"
            f"⏳ Days Remaining: {remaining}")
        return

    msg = bot.send_message(chat_id, "Enter Student Name:")
    bot.register_next_step_handler(msg, get_grade)

# ================= REGISTRATION =================

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
    kb.add("5 Days Free Trial")
    kb.add("2 Week - 300 LKR")
    kb.add("1 Month - 700 LKR")

    msg = bot.send_message(message.chat.id, "Select Plan:", reply_markup=kb)
    bot.register_next_step_handler(msg, get_target)

def get_target(message):

    chat_id = message.chat.id

    if "5 Days" in message.text:
        plan = "5 Days Free Trial"
    elif "2 Week" in message.text:
        plan = "2 Week"
    else:
        plan = "1 Month"

    user_data[chat_id]["plan"] = plan

    msg = bot.send_message(chat_id,
        "Your Target?",
        reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, finish_registration)

def finish_registration(message):

    chat_id = message.chat.id
    user_data[chat_id]["target"] = message.text

    bot.send_message(chat_id, BANK_DETAILS)
    msg = bot.send_message(chat_id, "Upload Payment Receipt:")
    bot.register_next_step_handler(msg, save_receipt)

# ================= RECEIPT =================

def save_receipt(message):

    if not message.photo:
        bot.send_message(message.chat.id, "Please upload image.")
        return

    chat_id = message.chat.id
    file_id = message.photo[-1].file_id
    data = user_data.get(chat_id)

    if not data:
        bot.send_message(chat_id, "Session expired.")
        return

    cursor.execute("""
    INSERT OR REPLACE INTO students
    (telegram_id,name,grade,exam_info,subjects,parent_phone,weekly_schedule,plan,target,status,receipt_file_id)
    VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (chat_id,data["name"],data["grade"],data["exam_info"],
          data["subjects"],data["parent_phone"],data["weekly_schedule"],
          data["plan"],data["target"],"pending",file_id))
    conn.commit()

    bot.send_message(chat_id, "✅ Waiting for Admin Approval.")

    bot.send_photo(ADMIN_ID, file_id,
        caption=f"NEW STUDENT\n{data['name']}\n/approve_{chat_id} link")

# ================= APPROVE =================

@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.text.startswith("/approve_"))
def approve(message):

    parts = message.text.split()

    if len(parts) < 2:
        bot.send_message(ADMIN_ID, "Format:\n/approve_USERID link")
        return

    tg_id = int(parts[0].split("_")[1])
    link = parts[1]

    cursor.execute("SELECT plan FROM students WHERE telegram_id=?", (tg_id,))
    row = cursor.fetchone()

    if not row:
        bot.send_message(ADMIN_ID, "Student not found.")
        return

    duration = 5 if row[0]=="5 Days Free Trial" else 14 if row[0]=="2 Week" else 30

    join_date = datetime.now()
    expiry_date = join_date + timedelta(days=duration)

    cursor.execute("""
    UPDATE students
    SET status='approved',
        join_date=?,
        expiry_date=?,
        notion_link=?
    WHERE telegram_id=?
    """,(join_date.strftime("%Y-%m-%d"),
         expiry_date.strftime("%Y-%m-%d"),
         link,tg_id))
    conn.commit()

    bot.send_message(tg_id, f"🎉 Approved!\nExpire: {expiry_date.strftime('%Y-%m-%d')}")
    bot.send_message(ADMIN_ID, "✅ Approved.")

# ================= DAILY CHECK =================

@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.text == "/dailycheck")
def daily_check_send(message):

    cursor.execute("SELECT telegram_id FROM students WHERE status='approved'")
    rows = cursor.fetchall()

    for row in rows:
        bot.send_message(row[0],
            "📅 Did you complete today's study?\nReply YES or NO")

    bot.send_message(ADMIN_ID, "✅ Daily check sent.")

# ================= SAVE RESPONSE =================

@bot.message_handler(func=lambda m: m.text and m.text.upper() in ["YES","NO"])
def save_response(message):

    chat_id = message.chat.id

    cursor.execute("SELECT status,name FROM students WHERE telegram_id=?", (chat_id,))
    row = cursor.fetchone()

    if not row or row[0]!="approved":
        return

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
    UPDATE students
    SET last_confirm=?
    WHERE telegram_id=?
    """,(f"{today} - {message.text.upper()}",chat_id))
    conn.commit()

    bot.send_message(chat_id,"✅ Saved.")
    bot.send_message(ADMIN_ID,
        f"{row[1]} ({chat_id}) replied: {message.text.upper()}")

# ================= TODAY REPORT =================

@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.text == "/todayreport")
def today_report(message):

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
    SELECT name,telegram_id FROM students
    WHERE last_confirm LIKE ?
    """,(f"{today} - YES%",))

    rows = cursor.fetchall()

    if not rows:
        bot.send_message(ADMIN_ID,"No YES responses today.")
        return

    report = "📊 TODAY YES LIST\n\n"

    for name,tg_id in rows:
        report += f"{name} ({tg_id})\n"

    bot.send_message(ADMIN_ID,report)

# ================= EXPIRE CHECK =================

def expire_check():
    while True:
        cursor.execute("SELECT telegram_id,expiry_date FROM students WHERE status='approved'")
        rows = cursor.fetchall()

        for tg_id,expiry in rows:
            if datetime.now() >= datetime.strptime(expiry,"%Y-%m-%d"):
                cursor.execute("UPDATE students SET status='expired' WHERE telegram_id=?",(tg_id,))
                conn.commit()
                bot.send_message(tg_id,"⚠️ Plan expired.")
                bot.send_message(ADMIN_ID,f"{tg_id} expired.")

        time.sleep(86400)

threading.Thread(target=expire_check,daemon=True).start()

print("🔥 BOT RUNNING...")
bot.infinity_polling(skip_pending=True)


