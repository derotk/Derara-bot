#!/usr/bin/env python3
"""
Confessly - Telegram Anonymous Confession Bot
python-telegram-bot v20+ (async)
"""

import re
import html
from typing import Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Chat,
    User,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8603569259:AAFxDtTxX96ZWOAhHhUjf7PhlmXodRauRIU"
CHANNEL_ID = "@its_derara"
ADMIN_ID = 6437321990

# ==================== DATA STORAGE ====================
pending_confessions: Dict[int, dict] = {}
approved_confessions: Dict[int, dict] = {}
banned_users: set = set()
reactions: Dict[int, Dict[str, set]] = defaultdict(lambda: {"❤️": set(), "😂": set(), "😱": set(), "👎": set()})
comments_tracking: Dict[int, dict] = {}
next_confession_id = 1
next_comment_id = 1
total_submitted = 0
total_approved = 0
total_rejected = 0
total_comments = 0

# ==================== FILTERING ====================
BAD_WORDS = {"badword1", "badword2", "offensive"}  # Replace with actual list

def contains_bad_words(text: str) -> bool:
    text_lower = text.lower()
    for word in BAD_WORDS:
        if re.search(rf'\b{re.escape(word)}\b', text_lower):
            return True
    return False

def contains_link(text: str) -> bool:
    url_pattern = r'https?://[^\s]+|www\.[^\s]+'
    return bool(re.search(url_pattern, text, re.IGNORECASE))

def contains_phone(text: str) -> bool:
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}'
    return bool(re.search(phone_pattern, text))

def is_valid_confession(text: str) -> Tuple[bool, Optional[str]]:
    if contains_link(text):
        return False, "Links are not allowed."
    if contains_phone(text):
        return False, "Phone numbers are not allowed."
    if contains_bad_words(text):
        return False, "Inappropriate language detected."
    if len(text.strip()) < 1:
        return False, "Message cannot be empty."
    return True, None

# ==================== HELPER FUNCTIONS ====================
def escape_markdown(text: str) -> str:
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in special_chars else char for char in text)

def get_confession_link(confession_id: int) -> str:
    if confession_id not in approved_confessions:
        return ""
    msg_id = approved_confessions[confession_id]["channel_message_id"]
    if CHANNEL_ID.startswith("@"):
        return f"https://t.me/{CHANNEL_ID[1:]}/{msg_id}"
    return ""

# ==================== CONVERSATION STATES ====================
WAITING_CONFESSION = 1
WAITING_COMMENT = 2
WAITING_UNBAN_USER_ID = 3
WAITING_DELETE_CONFESSION_ID = 4

# ==================== START COMMAND ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message with Send Confession button."""
    user = update.effective_user
    welcome_text = (
        f"<b>Welcome to Confessly, {html.escape(user.first_name)}!</b>\n\n"
        "Share your secrets anonymously. Your confession will be posted after admin approval.\n"
        "You can also comment anonymously on others' confessions."
    )
    keyboard = [[InlineKeyboardButton("📝 Send Confession", callback_data="confess")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )

# ==================== CONFESSION CONVERSATION ====================
async def confess_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in banned_users:
        await query.edit_message_text("❌ You are banned from using this bot.")
        return ConversationHandler.END

    await query.edit_message_text("✍️ Please type your confession. Keep it anonymous and respectful.")
    return WAITING_CONFESSION

async def receive_confession(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if user.id in banned_users:
        await update.message.reply_text("❌ You are banned.")
        return ConversationHandler.END

    text = update.message.text
    valid, reason = is_valid_confession(text)
    if not valid:
        await update.message.reply_text(f"❌ Invalid confession: {reason}\nPlease try again.")
        return WAITING_CONFESSION

    global next_confession_id, total_submitted
    confession_id = next_confession_id
    next_confession_id += 1
    pending_confessions[confession_id] = {"user_id": user.id, "text": text}
    total_submitted += 1

    await update.message.reply_text("⏳ Your confession has been submitted and is waiting for admin approval.")

    admin_text = (
        f"🆕 New Confession Request\n\n"
        f"User ID: <code>{user.id}</code>\n"
        f"Confession ID: <code>{confession_id}</code>\n\n"
        f"Message:\n{html.escape(text)}"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{confession_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{confession_id}"),
            InlineKeyboardButton("🚫 Ban User", callback_data=f"ban_{confession_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    except Exception as e:
        print(f"Failed to notify admin: {e}")

    return ConversationHandler.END

async def confess_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Confession cancelled.")
    return ConversationHandler.END

# ==================== ADMIN APPROVAL CALLBACKS ====================
async def admin_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ You are not authorized.")
        return

    confession_id = int(query.data.split("_")[1])
    if confession_id not in pending_confessions:
        await query.edit_message_text("❌ Confession not found or already processed.")
        return

    confession = pending_confessions.pop(confession_id)
    text = confession["text"]
    user_id_conf = confession["user_id"]

    global total_approved
    channel_text = (
        f"💌 New Anonymous Confession\n\n"
        f"{text}\n\n"
        f"#Confession #{confession_id}"
    )
    try:
        sent_message: Message = await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=channel_text,
        )
        approved_confessions[confession_id] = {
            "channel_message_id": sent_message.message_id,
            "text": text,
            "user_id": user_id_conf,
        }
        total_approved += 1

        keyboard = [
            [
                InlineKeyboardButton("❤️ 0", callback_data=f"reaction_❤️_{confession_id}"),
                InlineKeyboardButton("😂 0", callback_data=f"reaction_😂_{confession_id}"),
                InlineKeyboardButton("😱 0", callback_data=f"reaction_😱_{confession_id}"),
                InlineKeyboardButton("👎 0", callback_data=f"reaction_👎_{confession_id}"),
            ],
            [InlineKeyboardButton("💬 Comment", callback_data=f"comment_{confession_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.edit_message_reply_markup(
            chat_id=CHANNEL_ID,
            message_id=sent_message.message_id,
            reply_markup=reply_markup,
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Failed to post to channel: {e}")
        pending_confessions[confession_id] = confession
        return

    try:
        await context.bot.send_message(
            chat_id=user_id_conf,
            text="✅ Your confession has been approved and posted anonymously!",
        )
    except Exception:
        pass

    await query.edit_message_text(f"✅ Confession #{confession_id} approved and posted.")

async def admin_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Not authorized.")
        return

    confession_id = int(query.data.split("_")[1])
    if confession_id not in pending_confessions:
        await query.edit_message_text("❌ Confession not found.")
        return

    confession = pending_confessions.pop(confession_id)
    user_id = confession["user_id"]
    global total_rejected
    total_rejected += 1

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Your confession was rejected by the admin.",
        )
    except Exception:
        pass

    await query.edit_message_text(f"❌ Confession #{confession_id} rejected.")

async def admin_ban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Not authorized.")
        return

    confession_id = int(query.data.split("_")[1])
    if confession_id not in pending_confessions:
        await query.edit_message_text("❌ Confession not found.")
        return

    confession = pending_confessions.pop(confession_id)
    user_id = confession["user_id"]
    banned_users.add(user_id)
    global total_rejected
    total_rejected += 1

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="🚫 You have been banned from using Confessly.",
        )
    except Exception:
        pass

    await query.edit_message_text(f"🚫 User {user_id} banned and confession #{confession_id} rejected.")

# ==================== REACTION HANDLERS ====================
async def reaction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    _, reaction, confession_id_str = query.data.split("_")
    confession_id = int(confession_id_str)

    if confession_id not in approved_confessions:
        await query.answer("❌ Confession not found.", show_alert=True)
        return

    # Remove user from any previous reaction
    for r in ["❤️", "😂", "😱", "👎"]:
        if user_id in reactions[confession_id][r]:
            reactions[confession_id][r].remove(user_id)
            break

    reactions[confession_id][reaction].add(user_id)
    await update_reaction_buttons(context, confession_id)

async def update_reaction_buttons(context: ContextTypes.DEFAULT_TYPE, confession_id: int):
    if confession_id not in approved_confessions:
        return
    msg_id = approved_confessions[confession_id]["channel_message_id"]
    counts = reactions[confession_id]
    keyboard = [
        [
            InlineKeyboardButton(f"❤️ {len(counts['❤️'])}", callback_data=f"reaction_❤️_{confession_id}"),
            InlineKeyboardButton(f"😂 {len(counts['😂'])}", callback_data=f"reaction_😂_{confession_id}"),
            InlineKeyboardButton(f"😱 {len(counts['😱'])}", callback_data=f"reaction_😱_{confession_id}"),
            InlineKeyboardButton(f"👎 {len(counts['👎'])}", callback_data=f"reaction_👎_{confession_id}"),
        ],
        [InlineKeyboardButton("💬 Comment", callback_data=f"comment_{confession_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await context.bot.edit_message_reply_markup(
            chat_id=CHANNEL_ID,
            message_id=msg_id,
            reply_markup=reply_markup,
        )
    except Exception as e:
        print(f"Failed to update reaction buttons: {e}")

# ==================== COMMENT CONVERSATION ====================
async def comment_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    if user.id in banned_users:
        await query.edit_message_text("❌ You are banned from commenting.")
        return ConversationHandler.END

    confession_id = int(query.data.split("_")[1])
    if confession_id not in approved_confessions:
        await query.edit_message_text("❌ Confession not found.")
        return ConversationHandler.END

    context.user_data["comment_confession_id"] = confession_id
    await query.edit_message_text(
        f"✍️ Type your anonymous comment for Confession #{confession_id}\n"
        "(Your comment will be posted as a reply in the channel.)"
    )
    return WAITING_COMMENT

async def receive_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if user.id in banned_users:
        await update.message.reply_text("❌ You are banned.")
        return ConversationHandler.END

    text = update.message.text
    valid, reason = is_valid_confession(text)
    if not valid:
        await update.message.reply_text(f"❌ Invalid comment: {reason}\nPlease try again.")
        return WAITING_COMMENT

    confession_id = context.user_data.get("comment_confession_id")
    if not confession_id or confession_id not in approved_confessions:
        await update.message.reply_text("❌ Confession not found. Please start over.")
        return ConversationHandler.END

    global next_comment_id, total_comments
    comment_id = next_comment_id
    next_comment_id += 1

    channel_msg_id = approved_confessions[confession_id]["channel_message_id"]
    comment_text = f"💬 Anonymous Comment\n\n{text}"
    try:
        sent = await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=comment_text,
            reply_to_message_id=channel_msg_id,
        )
        comments_tracking[comment_id] = {
            "confession_id": confession_id,
            "user_id": user.id,
            "message_id": sent.message_id,
        }
        total_comments += 1
        await update.message.reply_text("✅ Your comment was posted anonymously!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to post comment: {e}")

    context.user_data.pop("comment_confession_id", None)
    return ConversationHandler.END

async def comment_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Comment cancelled.")
    return ConversationHandler.END

# ==================== ADMIN PANEL ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📂 Pending", callback_data="admin_pending")],
        [InlineKeyboardButton("🚫 Banned Users", callback_data="admin_banned")],
        [InlineKeyboardButton("🔓 Unban User", callback_data="admin_unban")],
        [InlineKeyboardButton("🗑 Delete Confession", callback_data="admin_delete")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Admin Panel", reply_markup=reply_markup)

async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Unauthorized.")
        return

    stats_text = (
        f"<b>Statistics</b>\n\n"
        f"Total submitted: {total_submitted}\n"
        f"Approved: {total_approved}\n"
        f"Rejected: {total_rejected}\n"
        f"Total comments: {total_comments}\n"
        f"Pending: {len(pending_confessions)}"
    )
    await query.edit_message_text(stats_text, parse_mode=ParseMode.HTML)

async def admin_pending_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Unauthorized.")
        return

    if not pending_confessions:
        await query.edit_message_text("No pending confessions.")
        return

    ids = sorted(pending_confessions.keys())
    text = "📂 Pending Confession IDs:\n" + "\n".join(f"• {cid}" for cid in ids)
    await query.edit_message_text(text)

async def admin_banned_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Unauthorized.")
        return

    if not banned_users:
        await query.edit_message_text("No banned users.")
        return

    text = "🚫 Banned User IDs:\n" + "\n".join(f"• {uid}" for uid in banned_users)
    await query.edit_message_text(text)

# Unban conversation
async def admin_unban_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Unauthorized.")
        return ConversationHandler.END

    await query.edit_message_text("Please send the user ID to unban:")
    return WAITING_UNBAN_USER_ID

async def admin_unban_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return ConversationHandler.END

    try:
        user_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please enter a number.")
        return WAITING_UNBAN_USER_ID

    if user_id in banned_users:
        banned_users.remove(user_id)
        await update.message.reply_text(f"✅ User {user_id} has been unbanned.")
    else:
        await update.message.reply_text(f"❌ User {user_id} is not in banned list.")

    return ConversationHandler.END

async def admin_unban_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Unban cancelled.")
    return ConversationHandler.END

# Delete confession conversation
async def admin_delete_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Unauthorized.")
        return ConversationHandler.END

    await query.edit_message_text("Please send the confession ID to delete:")
    return WAITING_DELETE_CONFESSION_ID

async def admin_delete_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return ConversationHandler.END

    try:
        confession_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Invalid confession ID. Please enter a number.")
        return WAITING_DELETE_CONFESSION_ID

    if confession_id not in approved_confessions:
        await update.message.reply_text(f"❌ Confession #{confession_id} not found.")
        return ConversationHandler.END

    msg_id = approved_confessions[confession_id]["channel_message_id"]
    try:
        await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=msg_id)
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to delete message: {e}")
        return ConversationHandler.END

    del approved_confessions[confession_id]
    if confession_id in reactions:
        del reactions[confession_id]

    await update.message.reply_text(f"✅ Confession #{confession_id} deleted from channel.")
    return ConversationHandler.END

async def admin_delete_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Deletion cancelled.")
    return ConversationHandler.END

# ==================== MAIN ====================
def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    confess_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(confess_entry, pattern="^confess$")],
        states={
            WAITING_CONFESSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_confession)],
        },
        fallbacks=[CommandHandler("cancel", confess_cancel)],
    )

    comment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(comment_entry, pattern="^comment_")],
        states={
            WAITING_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_comment)],
        },
        fallbacks=[CommandHandler("cancel", comment_cancel)],
    )

    unban_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_unban_entry, pattern="^admin_unban$")],
        states={
            WAITING_UNBAN_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_unban_receive)],
        },
        fallbacks=[CommandHandler("cancel", admin_unban_cancel)],
    )

    delete_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_delete_entry, pattern="^admin_delete$")],
        states={
            WAITING_DELETE_CONFESSION_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_delete_receive)],
        },
        fallbacks=[CommandHandler("cancel", admin_delete_cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(confess_conv)
    application.add_handler(comment_conv)
    application.add_handler(CallbackQueryHandler(admin_approve_callback, pattern="^approve_"))
    application.add_handler(CallbackQueryHandler(admin_reject_callback, pattern="^reject_"))
    application.add_handler(CallbackQueryHandler(admin_ban_callback, pattern="^ban_"))
    application.add_handler(CallbackQueryHandler(reaction_callback, pattern="^reaction_"))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(admin_stats_callback, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(admin_pending_callback, pattern="^admin_pending$"))
    application.add_handler(CallbackQueryHandler(admin_banned_callback, pattern="^admin_banned$"))
    application.add_handler(unban_conv)
    application.add_handler(delete_conv)

    print("Bot started...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()