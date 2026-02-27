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
notion_link TEXT
)
""")

# 🔥 NEW TABLE (DOES NOT TOUCH OLD DATA)
cursor.execute("""
CREATE TABLE IF NOT EXISTS daily_confirm (
id INTEGER PRIMARY KEY AUTOINCREMENT,
telegram_id INTEGER,
confirm_date TEXT,
response TEXT
)
""")

conn.commit()

user_data = {}

# ================= DAILY TASK SEND =================

@bot.message_handler(commands=['dailytaskcomfire'])
def send_daily_confirm(message):

    if message.chat.id != ADMIN_ID:
        return

    cursor.execute("SELECT telegram_id FROM students WHERE status='approved'")
    students = cursor.fetchall()

    if not students:
        bot.send_message(ADMIN_ID, "❌ No approved students.")
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("YES ✅", "NO ❌")

    for (tg_id,) in students:
        bot.send_message(
            tg_id,
            "📚 Did you complete today's study task?\n\nReply YES or NO",
            reply_markup=kb
        )

    bot.send_message(ADMIN_ID, "✅ Daily confirmation sent to all approved students.")

# ================= STUDENT YES/NO HANDLE =================

@bot.message_handler(func=lambda m: m.text in ["YES ✅", "NO ❌"])
def handle_confirmation(message):

    chat_id = message.chat.id
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT status FROM students WHERE telegram_id=?", (chat_id,))
    row = cursor.fetchone()

    if not row or row[0] != "approved":
        return

    # prevent duplicate
    cursor.execute("""
    SELECT * FROM daily_confirm
    WHERE telegram_id=? AND confirm_date=?
    """, (chat_id, today))

    if cursor.fetchone():
        bot.send_message(chat_id, "⚠️ You already responded today.")
        return

    response = "YES" if "YES" in message.text else "NO"

    cursor.execute("""
    INSERT INTO daily_confirm (telegram_id, confirm_date, response)
    VALUES (?, ?, ?)
    """, (chat_id, today, response))

    conn.commit()

    bot.send_message(chat_id, "✅ Response recorded.")

# ================= TODAY REPORT =================

@bot.message_handler(commands=['todayreport'])
def today_report(message):

    if message.chat.id != ADMIN_ID:
        return

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
    SELECT s.name, d.telegram_id
    FROM daily_confirm d
    JOIN students s ON d.telegram_id = s.telegram_id
    WHERE d.confirm_date=? AND d.response='YES'
    """, (today,))

    rows = cursor.fetchall()

    if not rows:
        bot.send_message(ADMIN_ID, "❌ No students confirmed YES today.")
        return

    text = "📊 TODAY CONFIRMED STUDENTS (YES)\n\n"

    for name, tg_id in rows:
        text += f"👤 {name} (ID: {tg_id})\n"

    bot.send_message(ADMIN_ID, text)

# ================= YOUR ORIGINAL CODE BELOW (UNCHANGED) =================

# (Registration, approval, expiry system same as before)

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

threading.Thread(target=daily_check, daemon=True).start()

print("🔥 FINAL PREMIUM BOT RUNNING WITH DAILY CONFIRM SYSTEM...")

bot.infinity_polling(skip_pending=True)
