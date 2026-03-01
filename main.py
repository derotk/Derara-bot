import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8625167357:AAHqVydRGnwl_q4Zvrfb5QxR6uEv90NHBvQ"
WEB_APP_URL = "https://deroearn.ct.ws"

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
        [InlineKeyboardButton("💰 OPEN ADSCASH", web_app={"url": WEB_APP_URL})]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(
        photo=photo_url,
        caption=caption,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("AdsCash Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()