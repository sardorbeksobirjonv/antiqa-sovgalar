import json
import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = "8248977779:AAFo0QOatTz-WJL19Kxe26JAP1JjWxw9ABg"
ADMIN_ID = 7752032178
CHANNEL_USERNAME = "@dev_spacce"   # @ bilan yoziladi

USERS_FILE = "users.json"
QUESTION_FILE = "question.json"


# ================= DATABASE =================

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}

    with open(USERS_FILE, "r") as f:
        users = json.load(f)

    for uid in users:
        users[uid].setdefault("score", 0)
        users[uid].setdefault("correct", 0)
        users[uid].setdefault("wrong", 0)
        users[uid].setdefault("answered", False)

    save_users(users)
    return users


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


def load_question():
    if not os.path.exists(QUESTION_FILE):
        return {}
    with open(QUESTION_FILE, "r") as f:
        return json.load(f)


def save_question(q):
    with open(QUESTION_FILE, "w") as f:
        json.dump(q, f, indent=4)


# ================= OBUNA TEKSHIRISH =================

async def check_subscription(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


def join_channel_button():
    keyboard = [
        [InlineKeyboardButton("📢 Kanalga qo‘shilish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ================= USER MENU =================

def user_menu():
    keyboard = [["👤 Shaxsiy kabinet"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ================= ADMIN MENU =================

def admin_menu():
    keyboard = [
        [InlineKeyboardButton("📝 Savol joylash", callback_data="add_question")],
        [InlineKeyboardButton("📢 Reklama", callback_data="broadcast")],
        [InlineKeyboardButton("👥 Userlar soni", callback_data="users_count")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users = load_users()

    if not await check_subscription(user.id, context):
        await update.message.reply_text(
            "❌ <b>Botdan foydalanish uchun kanalga obuna bo‘ling!</b>",
            parse_mode="HTML",
            reply_markup=join_channel_button()
        )
        return

    if str(user.id) not in users:
        users[str(user.id)] = {
            "score": 0,
            "correct": 0,
            "wrong": 0,
            "answered": False
        }
        save_users(users)

    if user.id == ADMIN_ID:
        await update.message.reply_text(
            "👑 <b>ADMIN PANEL</b>",
            parse_mode="HTML",
            reply_markup=admin_menu()
        )
    else:
        await update.message.reply_text(
            "🎉 <b>Xush kelibsiz!</b>\nSavol kelishini kuting 🔔",
            parse_mode="HTML",
            reply_markup=user_menu()
        )


# ================= CALLBACK =================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    users = load_users()

    # 🔥 OBUNA TEKSHIRISH
    if query.data == "check_sub":
        if await check_subscription(query.from_user.id, context):
            await query.message.delete()
            await query.message.reply_text(
                "✅ Obuna tasdiqlandi!\nEndi botdan foydalanishingiz mumkin.",
                reply_markup=user_menu()
            )
        else:
            await query.answer("❌ Hali kanalga qo‘shilmagansiz!", show_alert=True)
        return

    if query.from_user.id != ADMIN_ID:
        return

    if query.data == "add_question":
        context.user_data["state"] = "question_text"
        await query.message.edit_text("📝 Savol matnini yuboring:")

    elif query.data == "broadcast":
        context.user_data["state"] = "broadcast"
        await query.message.edit_text("📢 Reklama matnini yuboring:")

    elif query.data == "users_count":
        await query.message.edit_text(
            f"👥 Userlar soni: {len(users)}",
            reply_markup=admin_menu()
        )


# ================= TEXT HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    user = update.effective_user
    user_id_str = str(user.id)
    text = update.message.text.strip()

    # 🔥 OBUNA TEKSHIRISH
    if not await check_subscription(user.id, context):
        await update.message.reply_text(
            "❌ Avval kanalga obuna bo‘ling!",
            reply_markup=join_channel_button()
        )
        return

    # ===== SHAXSIY KABINET =====
    if text == "👤 Shaxsiy kabinet":
        data = users[user_id_str]
        await update.message.reply_text(
            f"👤 SHAXSIY KABINET\n\n"
            f"⭐ Ball: {data['score']}\n"
            f"✅ To‘g‘ri: {data['correct']}\n"
            f"❌ Xato: {data['wrong']}",
            reply_markup=user_menu()
        )
        return

    # ===== ADMIN =====
    if user.id == ADMIN_ID:

        if context.user_data.get("state") == "question_text":
            context.user_data["new_question"] = text
            context.user_data["state"] = "question_answer"
            await update.message.reply_text("✅ Endi to‘g‘ri javobni yuboring:")
            return

        if context.user_data.get("state") == "question_answer":

            save_question({
                "text": context.user_data["new_question"],
                "answer": text.lower()
            })

            for uid in users:
                users[uid]["answered"] = False

            save_users(users)

            for uid in users:
                if int(uid) == ADMIN_ID:
                    continue
                try:
                    await context.bot.send_message(
                        uid,
                        f"✨ YANGI SAVOL!\n\n{context.user_data['new_question']}"
                    )
                except:
                    pass

            context.user_data["state"] = None
            await update.message.reply_text("✅ Savol yuborildi!", reply_markup=admin_menu())
            return


    # ===== USER JAVOBI =====
    q = load_question()
    if not q:
        await update.message.reply_text("⏳ Hozir savol yo‘q.")
        return

    if users[user_id_str]["answered"]:
        await update.message.reply_text("⚠️ Siz allaqachon javob bergansiz.")
        return

    correct = q.get("answer", "").lower()

    if text.lower() == correct:
        users[user_id_str]["score"] += 1
        users[user_id_str]["correct"] += 1
        users[user_id_str]["answered"] = True
        save_users(users)

        await update.message.reply_text("🎉 To‘g‘ri javob! +1 ball")

    else:
        users[user_id_str]["wrong"] += 1
        users[user_id_str]["answered"] = True
        save_users(users)

        await update.message.reply_text("❌ Noto‘g‘ri javob.")


# ================= MAIN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot ishga tushdi...")
app.run_polling()
