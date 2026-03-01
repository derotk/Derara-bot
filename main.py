import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8625167357:AAHqVydRGnwl_q4Zvrfb5QxR6uEv90NHBvQ"
WEB_APP_URL = "https://deroearn.ct.ws"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command with a longer text."""
    # Photo (URL, local path, or file_id)
    photo_url = "https://t.me/AdsCashOfficial/3"

    # Longer caption (can be up to 1024 characters)
    caption = (
        "🎉 **Welcome to Our Awesome Bot!** 🎉\n\n"
        "We're thrilled to have you here. This bot demonstrates how to combine a photo, "
        "a descriptive message, and a mini app launcher in one command.\n\n"
        "✨ **What can you do?**\n"
        "• Explore our interactive Mini App by clicking the button below.\n"
        "• Get updates and news right in this chat.\n"
        "• Enjoy a seamless experience powered by Telegram.\n\n"
        "👇 **Ready to dive in?** Click the button to open the Mini App and discover more!\n\n"
        "If you have any questions, feel free to contact our support. Have fun!"
    )

    # Inline button to open the Mini App
    keyboard = [
        [InlineKeyboardButton("🚀 Open Mini App", web_app={"url": WEB_APP_URL})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(
        photo=photo_url,
        caption=caption,
        reply_markup=reply_markup,
        parse_mode="Markdown"  # Enables bold text with **
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()