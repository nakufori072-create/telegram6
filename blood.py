import json
import os
import re
import random
import asyncio
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from flask import Flask
from threading import Thread

TOKEN = "8408250860:AAHpm6-nFzCii7ICdavYj7NVm7eAg87eH_Q"
GROUP_CHAT_ID = -4838155548
CHANNEL_ID = -1002999652378
ADMIN_CHANNEL_ID = -1003073103178
BALANCE_FILE = "user_balances.json"
GMAIL_FILE = "gmail_list.json"
STATS_FILE = "user_stats.json"
COUNTER_FILE = "counter.json"

# --- Load balances ---
if os.path.exists(BALANCE_FILE):
    with open(BALANCE_FILE, "r") as f:
        user_balances = {int(k): v for k, v in json.load(f).items()}
else:
    user_balances = {}

# --- Load gmail list ---
if os.path.exists(GMAIL_FILE):
    with open(GMAIL_FILE, "r") as f:
        gmail_list = json.load(f)
else:
    gmail_list = []

# --- Load stats ---
if os.path.exists(STATS_FILE):
    with open(STATS_FILE, "r") as f:
        user_stats = {int(k): v for k, v in json.load(f).items()}
else:
    user_stats = {}

# --- Load counter ---
if os.path.exists(COUNTER_FILE):
    with open(COUNTER_FILE, "r") as f:
        counter = json.load(f).get("count", 0)
else:
    counter = 0

def save_balances():
    with open(BALANCE_FILE, "w") as f:
        json.dump(user_balances, f)

def save_gmail_list():
    with open(GMAIL_FILE, "w") as f:
        json.dump(gmail_list, f)

def save_stats():
    with open(STATS_FILE, "w") as f:
        json.dump(user_stats, f)

def save_counter():
    with open(COUNTER_FILE, "w") as f:
        json.dump({"count": counter}, f)

def main_menu():
    return ReplyKeyboardMarkup(
        [["📩 Gmail Request", "💰 Balance"], ["🎫 Withdraw"]],
        resize_keyboard=True
    )

def payment_options():
    return ReplyKeyboardMarkup(
        [["Bkash", "Nagad", "Mobile Recharge"]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def extract_field(text, label):
    pattern = rf"{label}:\s*(.+?)(?=\n|$)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_recovery(text):
    match = re.search(r"Recovery email\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+.[a-zA-Z0-9-.]+)", text)
    return match.group(1) if match else None

def generate_random_dob():
    year = random.randint(1997, 2004)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return datetime(year, month, day).strftime("%-d %B %Y")

def generate_random_gender():
    return random.choice(["Male", "Female"])

# --- Global Maps ---
user_withdraw_state = {}
gmail_data_map = {}
user_to_group_msg_map = {}  
user_active_gmail = {}
active_gmails = set()
user_blocked = {}  

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_blocked.get(user_id):  
        await update.message.reply_text("🚫 আমাদের বটের নীতি লংঘনের কারণে আপনাকে ব্লক করা হয়েছে।")
        return
    await update.message.reply_text(
        "👋 আমাদের বটে আপনাকে স্বাগতম!\n\n📬 Gmail রিকোয়েস্ট করতে নিচের বাটনগুলো ব্যবহার করুন।",
        reply_markup=main_menu()
    )

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global counter
    user_id = update.message.from_user.id
    user_name = update.message.from_user.full_name
    text = update.message.text.strip()
    balance = user_balances.get(user_id, 0)

    if user_blocked.get(user_id):
        await update.message.reply_text("🚫 আমাদের বটের নীতি লংঘনের কারণে আপনাকে ব্লক করা হয়েছে।")
        return

    if text == "📩 Gmail Request":
        if user_id in user_active_gmail:
            await update.message.reply_text("🚫 আপনার নেওয়া জিমেইলটির কাজ সম্পন্ন করুন অথবা Cancel করুন।")
            return

        while gmail_list and gmail_list[0] in active_gmails:
            gmail_list.pop(0)
            save_gmail_list()

        if gmail_list:
            data = gmail_list.pop(0)
            save_gmail_list()
            active_gmails.add(data)

            name = extract_field(data, "First name")
            email = extract_field(data, "Email")
            password = extract_field(data, "Password")
            recovery = extract_recovery(data)

            if not all([name, email, password]):
                await update.message.reply_text("❌ ইনফরমেশন ফরম্যাট ভুল!")
                return

            dob = generate_random_dob()
            gender = generate_random_gender()

            msg = (
                f"👤 First name: `{name}`\n"
                f"✖️ Last name: `✖️`\n"
                f"📧 Gmail: `{email}`\n"
                f"🔐 Password: `{password}`\n"
                f"📨 Recovery Email: `{recovery}`\n"
                f"🎂 Date of birth: `{dob}`\n"
                f"⚥ Gender: `{gender}`\n\n"
                f"একাউন্ট টি খুলা হয়ে গেলে লগ আউট করে দিন,ধন্যবাদ😊"
            )

            gmail_data_map[user_id] = {"email": email, "raw": data}
            user_active_gmail[user_id] = data

            group_msg = await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=f"📤 Gmail sent to {user_name} (ID: {user_id}):\n\n{msg}",
                parse_mode="Markdown"
            )
            user_to_group_msg_map.setdefault(user_id, []).append((group_msg.message_id, email, data))

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Done ✅", callback_data=f"done:{user_id}")],
                [InlineKeyboardButton("❌ Cancel Registration", callback_data=f"cancel:{user_id}")]
            ])
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=buttons)
        else:
            await update.message.reply_text(
                "প্রিয় মেম্বার, বর্তমানে জিমেইল পাঠানো সম্ভব হচ্ছে না দয়া করে একটু পর আবার চেষ্টা করুন😊"
            )

    elif text == "💰 Balance":
        await update.message.reply_text(f"💼 আপনার ব্যালেন্স: *{balance} টাকা*", parse_mode="Markdown")

    elif text == "🎫 Withdraw":
        if balance >= 100:
            user_withdraw_state[user_id] = "awaiting_method"
            await update.message.reply_text("💳 কোন পেমেন্ট মেথড ব্যবহার করতে চান?", reply_markup=payment_options())
        else:
            await update.message.reply_text("🚫 আমাদের বট থেকে উইথড্র করার জন্য অন্তত 100 টাকা ব্যালেন্স থাকতে হবে।")

    elif text in ["Bkash", "Nagad", "Mobile Recharge"]:
        if user_withdraw_state.get(user_id) == "awaiting_method":
            user_withdraw_state[user_id] = f"awaiting_number:{text.lower()}"
            await update.message.reply_text(f"📱 অনুগ্রহ করে আপনার {text} নাম্বারটি দিন:")

    elif re.fullmatch(r'01[0-9]{9}', text) and user_id in user_withdraw_state:
        current_state = user_withdraw_state[user_id]
        if current_state.startswith("awaiting_number"):
            method = current_state.split(":")[1].capitalize()
            await update.message.reply_text("✅ উইথড্র রিকোয়েস্ট গ্রহণ করা হয়েছে!\n🕐 ২৪ ঘন্টার মধ্যে প্রক্রিয়া সম্পন্ন হবে।", reply_markup=main_menu())
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=f"📄 Withdraw Request:\n👤 {user_name}\n🆔 ID: {user_id}\n💳 Method: {method}\n📱 Number: {text}\n💰 Amount: {balance} টাকা"
            )
            user_balances[user_id] = 0
            save_balances()
            del user_withdraw_state[user_id]

async def auto_verify(user_id, context: ContextTypes.DEFAULT_TYPE):
    global counter
    if user_id not in gmail_data_map:
        return

    email = gmail_data_map[user_id]["email"]
    raw = gmail_data_map[user_id]["raw"]

    user_balances[user_id] = user_balances.get(user_id, 0) + 15
    save_balances()

    stats = user_stats.get(user_id, {"total_accounts": 0, "total_earnings": 0})
    stats["total_accounts"] += 1
    stats["total_earnings"] += 15
    user_stats[user_id] = stats
    save_stats()

    counter += 1
    save_counter()

    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ ধন্যবাদ! আপনার একাউন্ট এ *১৫ টাকা* যোগ হয়েছে,একাউন্ট টি Register না করেই Done চাপলে আপনার ব্যালেন্স কেটে নেওয়া হবে⚠️।",
        parse_mode="Markdown"
    )

    msg_infos = user_to_group_msg_map.get(user_id, [])
    for group_msg_id, e, raw_data in msg_infos:
        if e == email:
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=(
                    f"#{counter}️⃣ Gmail Verified Automatically:\n"
                    f"👤 User ID: {user_id}\n"
                    f"📧 Gmail: {email}\n"
                    f"💰 Balance: {user_balances[user_id]} টাকা\n"
                    f"📂 Accounts Opened: {stats['total_accounts']}\n"
                    f"💵 Total Earnings: {stats['total_earnings']} টাকা"
                ),
                reply_to_message_id=group_msg_id,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Reject Gmail", callback_data=f"reject:{user_id}:{email}")]
                ])
            )
            break

    active_gmails.discard(raw)
    if user_id in user_active_gmail:
        del user_active_gmail[user_id]
    if user_id in gmail_data_map:
        del gmail_data_map[user_id]

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("done:"):
        target_user = int(data.split(":")[1])
        if user_id != target_user:
            await query.edit_message_text("🚫 আপনি এই বাটন ব্যবহার করতে পারবেন না।")
            return
        await query.edit_message_text("⏳ আপনার জিমেইল ভেরিফাই হচ্ছে, দয়া করে অপেক্ষা করুন...")
        await asyncio.sleep(15)
        await auto_verify(target_user, context)

    elif data.startswith("cancel:"):
        target_user = int(data.split(":")[1])
        if user_id != target_user:
            await query.edit_message_text("🚫 আপনি এই বাটন ব্যবহার করতে পারবেন না।")
            return

        if user_id in user_active_gmail:
            gmail_list.insert(0, user_active_gmail[user_id])
            save_gmail_list()
            active_gmails.discard(user_active_gmail[user_id])
            del user_active_gmail[user_id]
        if user_id in gmail_data_map:
            del gmail_data_map[user_id]

        await query.edit_message_text("❌ আপনি জিমেইল Registration বাতিল করেছেন।")

    elif data.startswith("reject:"):
        _, target_user, target_email = data.split(":")
        target_user = int(target_user)

        await query.edit_message_text(
            f"❓ আপনি কি নিশ্চিত {target_user} এর Gmail ({target_email}) Reject করতে চান?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes", callback_data=f"confirm_reject:{target_user}:{target_email}")],
                [InlineKeyboardButton("❌ No", callback_data="cancel_reject")]
            ])
        )

    elif data.startswith("confirm_reject:"):
        _, target_user, target_email = data.split(":")
        target_user = int(target_user)

        msg_infos = user_to_group_msg_map.get(target_user, [])
        for msg_info in msg_infos:
            if msg_info[1] == target_email:
                raw = msg_info[2]

                user_balances[target_user] = max(user_balances.get(target_user, 0) - 15, 0)
                save_balances()

                gmail_list.insert(0, raw)
                save_gmail_list()
                active_gmails.discard(raw)

                if target_user in user_active_gmail:
                    del user_active_gmail[target_user]
                if target_user in gmail_data_map:
                    del gmail_data_map[target_user]

                await context.bot.send_message(
                    chat_id=target_user,
                    text=f"❌ আপনার কাজ করা \"{target_email}\" এই জিমেইলটি রেজিষ্ট্রেশন করা হয় নি, তাই আপনার একাউন্ট থেকে ১৫ টাকা কেটে নেওয়া হলো⚠️"
                )
                await query.edit_message_text(f"❌ ইউজারের Gmail Reject করা হলো ({target_email})")
                break

    elif data == "cancel_reject":
        await query.edit_message_text("❌ Reject অপারেশন বাতিল করা হলো।")

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.channel_post.text
    chat_id = update.channel_post.chat_id

    if chat_id == CHANNEL_ID:
        if "First name" in text and "Email" in text and "Password" in text:
            gmail_list.append(text)
            save_gmail_list()

    if chat_id == ADMIN_CHANNEL_ID:
        match = re.match(r"(\d+)\((add|block|unblock|rer)\)", text.strip())
        if match:
            target_id = int(match.group(1))
            action = match.group(2)

            if action == "add":
                user_balances[target_id] = user_balances.get(target_id, 0) + 15
                save_balances()
                await context.bot.send_message(target_id, "✅ আপনার একাউন্ট এ *১৫ টাকা* যোগ হয়েছে।", parse_mode="Markdown")
                await context.bot.send_message(ADMIN_CHANNEL_ID, f"✔️ {target_id} এর ব্যালেন্সে ১৫ টাকা যোগ করা হলো।")

            elif action == "block":
                user_blocked[target_id] = True
                await context.bot.send_message(target_id, "⚠️ আমাদের বটের নীতি লংঘনের কারণে আপনাকে ব্লক করা হলো।")
                await context.bot.send_message(ADMIN_CHANNEL_ID, f"⛔ {target_id} ব্লক করা হলো।")

            elif action == "unblock":
                if target_id in user_blocked:
                    del user_blocked[target_id]
                await context.bot.send_message(target_id, "✅ আপনাকে আনব্লক করা হয়েছে।")
                await context.bot.send_message(ADMIN_CHANNEL_ID, f"♻️ {target_id} আনব্লক করা হলো।")

            elif action == "rer":
                if target_id in user_active_gmail:
                    del user_active_gmail[target_id]
                if target_id in gmail_data_map:
                    del gmail_data_map[target_id]
                await context.bot.send_message(target_id, "✅ আপনি এখন আবারো Gmail নিতে পারবেন।")
                await context.bot.send_message(ADMIN_CHANNEL_ID, f"♻️ {target_id} এর Gmail reset করা হলো।")

# --- Flask server for Render port ---
flask_app = Flask("server")

@flask_app.route("/")
def index():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

def main():
    # Start Flask server in separate thread
    Thread(target=run_flask).start()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_user_message))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.CHANNEL, handle_channel_post))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()