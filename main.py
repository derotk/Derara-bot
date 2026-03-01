import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8625167357:AAHqVydRGnwl_q4Zvrfb5QxR6uEv90NHBvQ"
WEB_APP_URL = "https://deroearn.ct.ws"
BOT_USERNAME = "AdsCashsBot"  # Replace with your bot's username if different

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first_name = user.first_name if user.first_name else "User"

    photo_url = "https://t.me/AdsCashOfficial/3"
    caption = (
        f"💸 *WELCOME TO ADSCASH, {first_name.upper()}!* 💸\n\n"
        "*Earn real rewards* by simply watching ads inside our Mini App.\n\n"
        "🔥 *HOW IT WORKS:*\n"
        "• Watch ads\n"
        "• Earn coins instantly\n"
        "• Withdraw your balance easily\n\n"
        "🚀 *Tap the button below and start earning now!*"
    )

    keyboard = [
        [InlineKeyboardButton("💰 OPEN AdsCash", web_app={"url": WEB_APP_URL})],
        [
            InlineKeyboardButton("👥 Invite Users", callback_data="invite"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(
        photo=photo_url,
        caption=caption,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # Main menu keyboard
    main_keyboard = [
        [InlineKeyboardButton("💰 OPEN AdsCash", web_app={"url": WEB_APP_URL})],
        [
            InlineKeyboardButton("👥 Invite Users", callback_data="invite"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ]
    main_markup = InlineKeyboardMarkup(main_keyboard)

    if data == "invite":
        referral_link = f"https://t.me/{BOT_USERNAME}/AdsCash?startapp={user_id}"
        invite_text = (
            "🔗 *YOUR PERSONAL INVITE LINK*\n\n"
            f"`{referral_link}`\n\n"
            "📢 Tap on the link above to copy it, then share with friends!\n"
            "When they join using your link, you'll earn bonus rewards.\n\n"
            "💡 *Tip:* Post it in groups or chats to maximize earnings."
        )
        back_button = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        await query.edit_message_caption(
            caption=invite_text,
            reply_markup=InlineKeyboardMarkup(back_button),
            parse_mode="Markdown"
        )

    elif data == "help":
        help_text = (
            "🆘 *HELP & SUPPORT*\n\n"
            "If you have any questions or issues:\n"
            "• Join our support chat: [@AdsCashChat](https://t.me/AdsCashChat)\n"
            "• Our team is ready to assist you 24/7.\n\n"
            "📌 *FAQ*\n"
            "• How do I withdraw? – Use the withdraw option in the Mini App.\n"
            "• Why are ads not loading? – Check your internet and try again.\n"
            "• Is this free? – Absolutely, no payments required."
        )
        back_button = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        await query.edit_message_caption(
            caption=help_text,
            reply_markup=InlineKeyboardMarkup(back_button),
            parse_mode="Markdown"
        )

    elif data == "back":
        user = query.from_user
        first_name = user.first_name if user.first_name else "User"
        main_caption = (
            f"💸 *WELCOME TO ADSCASH, {first_name.upper()}!* 💸\n\n"
            "*Earn real rewards* by simply watching ads inside our Mini App.\n\n"
            "🔥 *HOW IT WORKS:*\n"
            "• Watch ads\n"
            "• Earn coins instantly\n"
            "• Withdraw your balance easily\n\n"
            "🚀 *Tap the button below and start earning now!*"
        )
        await query.edit_message_caption(
            caption=main_caption,
            reply_markup=main_markup,
            parse_mode="Markdown"
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("AdsCash Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()