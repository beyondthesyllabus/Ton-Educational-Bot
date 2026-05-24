import os
import io
import asyncio
import logging
import uvicorn
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from PIL import Image
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from openai import OpenAI

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# -------------------------------
# Environment Setup
# -------------------------------
load_dotenv("env/key.env")
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")  # Set to 'production' on Render

# -------------------------------
# Logging
# -------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -------------------------------
# In-Memory Event Logs
# -------------------------------
system_logs = []

def log_event(message: str, log_type: str = "info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_logs.append({
        "timestamp": timestamp,
        "message": message,
        "type": log_type
    })
    if len(system_logs) > 100:
        system_logs.pop(0)
    print(f"[{log_type.upper()}] {message}", flush=True)

# -------------------------------
# Fallback Responses (no AI key needed)
# -------------------------------
def get_ton_fallback_response(msg: str) -> str:
    msg_lower = msg.lower()
    if "what is ton" in msg_lower or "about ton" in msg_lower or "explain ton" in msg_lower:
        return (
            "**The Open Network (TON)** is a third-generation layer-1 blockchain designed by Telegram "
            "to onboard billions of users. It features:\n\n"
            "• **Infinite Dynamic Sharding**: Splits the load automatically to maintain sub-second transaction speeds.\n"
            "• **Ultra-Low Fees**: Transaction costs are a fraction of a cent.\n"
            "• **Telegram Integration**: Allows developers to build Mini Apps running directly inside Telegram."
        )
    elif "toncoin" in msg_lower or "native token" in msg_lower:
        return (
            "**Toncoin (TON)** is the native utility token of the TON Blockchain. Its key purposes include:\n\n"
            "• **Gas Fees**: Used to pay for executing smart contracts and transfers.\n"
            "• **Staking**: Locked by validators to secure the network, earning interest yield.\n"
            "• **Decentralized Services**: Used to pay for TON DNS, TON Storage, and Telegram Mini Apps."
        )
    elif "wallet" in msg_lower or "tonkeeper" in msg_lower:
        return (
            "To interact with TON, you need a crypto wallet. The main options are:\n\n"
            "• **@Wallet (Telegram)**: A custodial wallet built directly into Telegram settings.\n"
            "• **Tonkeeper / MyTonWallet**: Recommended non-custodial apps where you hold your own private key.\n\n"
            "*Security Tip: Never share your 24-word recovery phrase with anyone!*"
        )
    elif "smart contract" in msg_lower or "func" in msg_lower or "tact" in msg_lower:
        return (
            "TON uses a unique asynchronous model for smart contracts, written in two main languages:\n\n"
            "• **Tact**: A modern, developer-friendly language with strong typing and compile-time safety.\n"
            "• **FunC**: A lower-level, C-like language that offers maximum optimization and TVM access.\n\n"
            "Unlike Ethereum, TON smart contracts communicate via asynchronous messages."
        )
    elif "sharding" in msg_lower or "shard" in msg_lower or "scaling" in msg_lower:
        return (
            "**Dynamic Sharding** is a core architectural feature of TON:\n\n"
            "• **Dynamic Split & Merge**: Shardchains split when load increases and merge when it drops.\n"
            "• **Parallel Processing**: Each shardchain executes transactions in parallel for massive scaling.\n"
            "• **Masterchain Coordination**: Routes messages between shards and maintains validator sets."
        )
    else:
        return (
            "I'm here to help you learn about TON! I can answer questions about:\n\n"
            "• **What is TON?**\n"
            "• **What is Toncoin?**\n"
            "• **What wallets are available?**\n"
            "• **How to write smart contracts?**\n"
            "• **How does TON sharding work?**\n\n"
            "Configure a valid `OPENAI_API_KEY` in your environment for unrestricted AI chat."
        )

# -------------------------------
# Telegram Bot Handlers
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    log_event(f"Telegram: {username} used /start.", "info")
    await update.message.reply_text(
        "Hi, welcome to the TON Africa Telegram Bot! "
        "Ask me anything about the TON blockchain."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    log_event(f"Telegram: {username} used /help.", "info")
    await update.message.reply_text(
        "📚 Available Commands:\n"
        "/start - Welcome message\n"
        "/help - Show this help message\n"
        "You can also ask any TON-related question directly!"
    )

async def ton_qa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    user_msg = update.message.text.strip()
    log_event(f"Telegram: Message from {username}: '{user_msg}'", "info")

    if not openai_configured or not openai_client:
        fallback_reply = get_ton_fallback_response(user_msg)
        await update.message.reply_text(fallback_reply)
        return

    if "ton" in user_msg.lower() or "blockchain" in user_msg.lower():
        try:
            response = await asyncio.to_thread(
                openai_client.responses.create,
                prompt={
                    "id": "pmpt_6a12518928a4819598acc858c283a8540b5219277297c774",
                    "version": "2"
                },
                input=user_msg
            )
            answer = response.output_text
            log_event(f"Telegram: Answered question for {username}.", "success")
        except Exception as e:
            log_event(f"Telegram: OpenAI error: {e}", "error")
            answer = get_ton_fallback_response(user_msg)
        await update.message.reply_text(answer)
    else:
        await update.message.reply_text(
            "🤖 I specialize in TON Blockchain questions. Try asking about TON, "
            "Toncoin, wallets, staking, NFTs, or smart contracts."
        )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    log_event(f"Telegram: Photo received from {username}.", "info")
    try:
        photo_file = await update.message.photo[-1].get_file()
        file_bytes = await photo_file.download_as_bytearray()
        img = Image.open(io.BytesIO(bytes(file_bytes)))
        img_type = img.format
        img_size = img.size
        log_event(f"Telegram: Image verified ({img_type}, {img_size}).", "success")
        await update.message.reply_text(
            f"✅ Image received and verified as {img_type} ({img_size[0]}x{img_size[1]})."
        )
    except Exception as e:
        log_event(f"Telegram: Image processing failed: {e}", "error")
        await update.message.reply_text("⚠️ Uploaded file is not a valid image.")

# -------------------------------
# Global State
# -------------------------------
bot_app = None
bot_active = False
openai_client = None
openai_configured = False
system_prompt = ""

# -------------------------------
# FastAPI Lifespan
# -------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_app, bot_active, openai_client, openai_configured, system_prompt
    log_event("Initializing TON Africa server...", "system")

    # 1. Load TON Knowledge Base
    ton_knowledge = "TON (The Open Network) is a dynamic-sharded layer-1 blockchain."
    try:
        if os.path.exists("ton_knowledge.txt"):
            with open("ton_knowledge.txt", "r", encoding="utf-8") as f:
                ton_knowledge = f.read()
            log_event("TON knowledge base loaded successfully.", "success")
    except Exception as e:
        log_event(f"Error loading ton_knowledge.txt: {e}", "error")

    system_prompt = (
        "You are a helpful, expert AI assistant specializing in the TON (The Open Network) Blockchain. "
        "Use the following official TON knowledge base to answer user questions accurately. "
        "If a question is completely unrelated to TON, politely remind the user that your expertise "
        "is strictly limited to the TON blockchain ecosystem.\n\n"
        f"--- TON KNOWLEDGE BASE ---\n{ton_knowledge}\n--------------------------\n\n"
        "Format responses cleanly using markdown (bold text, bullet lists where appropriate)."
    )

    # 2. Configure OpenAI Client
    if OPENAI_API_KEY:
        try:
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
            openai_configured = True
            log_event("OpenAI client initialized successfully.", "success")
        except Exception as e:
            openai_configured = False
            log_event(f"OpenAI configuration error: {e}", "error")
    else:
        openai_configured = False
        log_event("OPENAI_API_KEY is missing. Running in fallback mode.", "warning")

    # 3. Start Telegram Bot (only in production to avoid 409 conflict locally)
    if TOKEN and ENVIRONMENT == "production":
        try:
            log_event("Starting Telegram bot polling...", "system")
            bot_app = ApplicationBuilder().token(TOKEN).build()
            bot_app.add_handler(CommandHandler("start", start))
            bot_app.add_handler(CommandHandler("help", help_command))
            bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), ton_qa))
            bot_app.add_handler(MessageHandler(filters.PHOTO, handle_image))

            try:
                await bot_app.bot.delete_webhook(drop_pending_updates=True)
                log_event("Webhook cleared successfully.", "success")
            except Exception as e:
                log_event(f"Webhook deletion warning: {e}", "warning")

            await bot_app.initialize()
            await bot_app.start()
            await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            bot_active = True
            log_event("Telegram Bot is running in the background.", "success")
        except Exception as e:
            bot_active = False
            log_event(f"Failed to start Telegram Bot: {e}", "error")
    else:
        bot_active = False
        if not TOKEN:
            log_event("BOT_TOKEN is missing. Telegram bot is disabled.", "warning")
        elif ENVIRONMENT != "production":
            log_event(f"Telegram bot disabled. ENVIRONMENT is '{ENVIRONMENT}', needs 'production'.", "warning")

    yield

    # Shutdown
    if bot_app and bot_active:
        log_event("Shutting down Telegram bot...", "system")
        try:
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()
            log_event("Telegram bot stopped.", "success")
        except Exception as e:
            log_event(f"Error during bot shutdown: {e}", "error")

# -------------------------------
# FastAPI App
# -------------------------------
app = FastAPI(
    title="TON Africa Educational Portal API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Request Schemas
# -------------------------------
class ChatRequest(BaseModel):
    message: str

# -------------------------------
# API Endpoints
# -------------------------------
@app.post("/api/chat")
async def api_chat(payload: ChatRequest):
    """AI Q&A endpoint."""
    user_msg = payload.message.strip()
    log_event(f"Web API: Chat request: '{user_msg}'", "info")

    if not openai_configured or not openai_client:
        fallback_reply = get_ton_fallback_response(user_msg)
        return {"reply": f"⚠️ *OpenAI API Key not configured. Showing local response:*\n\n{fallback_reply}"}

    try:
        response = await asyncio.to_thread(
            openai_client.responses.create,
            prompt={
                "id": "pmpt_6a12518928a4819598acc858c283a8540b5219277297c774",
                "version": "2"
            },
            input=user_msg
        )
        answer = response.output_text
        log_event("Web API: OpenAI reply sent.", "success")
        return {"reply": answer}
    except Exception as e:
        log_event(f"Web API: OpenAI error: {e}. Using fallback.", "error")
        fallback_reply = get_ton_fallback_response(user_msg)
        return {"reply": f"⚠️ *AI unavailable. Showing local response:*\n\n{fallback_reply}"}


@app.post("/api/upload")
async def api_upload(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None)
):
    """Upload and verify an image using Pillow."""
    log_event(f"Web API: Image upload '{file.filename}'", "info")
    try:
        file_bytes = await file.read()
        img = Image.open(io.BytesIO(file_bytes))
        img_format = img.format
        img_size = img.size
        img_mode = img.mode
        log_event(f"Web API: Image verified ({img_format}, {img_size}).", "success")
        ai_response = ""
        if prompt:
            ai_response = f"Verified image format as {img_format} with mode {img_mode}. Note: '{prompt}'"
        return {
            "filename": file.filename,
            "format": img_format,
            "size": img_size,
            "mode": img_mode,
            "ai_response": ai_response
        }
    except Exception as e:
        log_event(f"Web API: Image verification failed: {e}", "error")
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")


@app.get("/api/status")
async def api_status():
    """System status and telemetry."""
    return {
        "bot_active": bot_active,
        "credentials": {
            "BOT_TOKEN": "configured" if TOKEN else "missing",
            "OPENAI_API_KEY": "configured" if OPENAI_API_KEY else "missing"
        },
        "logs": system_logs
    }


@app.get("/api/health")
async def health_check():
    """Simple health check for Render."""
    return {"status": "ok"}


# -------------------------------
# Static Frontend Serving
# -------------------------------
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
else:
    log_event("Frontend folder not found. API-only mode.", "warning")

# -------------------------------
# Main Runner
# -------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    log_event(f"Starting server on http://0.0.0.0:{port}...", "system")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
