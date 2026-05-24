import logging
import os
import requests
from PIL import Image
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from dotenv import load_dotenv

# -------------------------------
# Load environment variables from key.env
# -------------------------------
load_dotenv("env/key.env")  # adjust if your key.env is in another folder
TOKEN = os.getenv("BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # required for AI answers

# -------------------------------
# Logging setup
# -------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -------------------------------
# Bot Handlers
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    await update.message.reply_text(
        "Hi, welcome to the TON Africa Telegram Bot. "
        "This bot is designed to educate you about TON and provide useful information automatically."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when /help is issued."""
    await update.message.reply_text(
        "📚 Available Commands:\n"
        "/start - Start the bot and see the welcome message\n"
        "/help - Show this help message\n"
        "You can also send messages and I will respond to TON-related questions!"
    )

# -------------------------------
# AI-powered TON Q&A Handler
# -------------------------------
async def ton_qa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Answer TON-related questions with AI (DeepSeek)."""
    user_msg = update.message.text.strip()
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        await update.message.reply_text("⚠️ AI is not available because no DeepSeek API key was set.")
        return

    # Only handle TON-related questions
    if "ton" in user_msg.lower() or "blockchain" in user_msg.lower():
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "deepseek-chat",  # valid model
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that answers questions about the TON Blockchain clearly and concisely."},
                    {"role": "user", "content": user_msg}
                ],
                "stream": False
            }

            response = requests.post(
                "https://api.deepseek.com/chat/completions",  # ✅ correct endpoint
                json=payload,
                headers=headers
            )
            data = response.json()

            if "choices" in data:
                answer = data["choices"][0]["message"]["content"]
            else:
                answer = "⚠️ Sorry, I couldn’t get a proper response from the AI."

        except Exception as e:
            answer = f"⚠️ Error connecting to DeepSeek API: {e}"

        await update.message.reply_text(answer)

    else:
        await update.message.reply_text(
            "🤖 I specialize in TON Blockchain questions. Try asking about TON, Toncoin, wallets, staking, NFTs, or smart contracts."
        )


# -------------------------------
# Handle uploaded images
# -------------------------------
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check uploaded images using Pillow."""
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # Get the last photo from the message
    photo_file = await update.message.photo[-1].get_file()
    file_path = f"downloads/{photo_file.file_id}.jpg"

    # Download the image
    await photo_file.download_to_drive(file_path)

    # Detect image type using Pillow
    try:
        with Image.open(file_path) as img:
            img_type = img.format
        await update.message.reply_text(f"✅ Image received and verified as {img_type}.")
    except Exception:
        await update.message.reply_text("⚠️ Uploaded file is not a valid image.")

# -------------------------------
# Main function
# -------------------------------
def main():
    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN not set in key.env file")

    # Build the bot application
    app = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), ton_qa))  # AI Q&A
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    # Clear webhook (non-blocking)
    try:
        app.bot.delete_webhook()
        logger.info("✅ Webhook cleared before starting polling.")
    except Exception as e:
        logger.warning(f"Webhook clearing failed: {e}")

    logger.info("🚀 TON Africa Bot is running...")
    app.run_polling()  # will keep running until CTRL+C

# -------------------------------
# Entry point
# -------------------------------
if __name__ == "__main__":
    main()
