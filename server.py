import os
import io
import logging
import asyncio
import requests
import uvicorn
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

from PIL import Image
from dotenv import load_dotenv
from openai import AsyncOpenAI

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
    # Keep only the last 100 log lines
    if len(system_logs) > 100:
        system_logs.pop(0)
    print(f"[{log_type.upper()}] {message}")

# Helper for fallback responses when OpenAI API is unavailable or has insufficient balance
def get_ton_fallback_response(msg: str) -> str:
    msg_lower = msg.lower()
    if "what is ton" in msg_lower or "about ton" in msg_lower or "explain ton" in msg_lower:
        return (
            "**The Open Network (TON)** is a third-generation layer-1 blockchain designed by Telegram "
            "to onboard billions of users. It features:\n\n"
            "• **Infinite Dynamic Sharding**: Splits the load automatically to maintain sub-second transaction speeds.\n"
            "• **Ultra-Low Fees**: Transaction costs are a fraction of a cent.\n"
            "• **Telegram Integration**: Allows developers to build Mini Apps running directly inside Telegram chat channels."
        )
    elif "toncoin" in msg_lower or "native token" in msg_lower:
        return (
            "**Toncoin (TON)** is the native utility token of the TON Blockchain. Its key purposes include:\n\n"
            "• **Gas Fees**: Used to pay for executing smart contracts and transfers.\n"
            "• **Staking**: Locked by validators to secure the network, earning interest yield.\n"
            "• **Decentralized Services**: Used to pay for TON DNS, TON Storage, and products inside Telegram Mini Apps."
        )
    elif "wallet" in msg_lower or "tonkeeper" in msg_lower:
        return (
            "To interact with TON, you need a crypto wallet. The main options are:\n\n"
            "• **@Wallet (Telegram)**: A custodial wallet built directly into Telegram settings, convenient for P2P transfers.\n"
            "• **Tonkeeper / MyTonWallet**: Recommended non-custodial apps where you hold your private key (seed phrase).\n\n"
            "*Security Tip: Never share your 24-word recovery phrase with anyone!*"
        )
    elif "smart contract" in msg_lower or "func" in msg_lower or "tact" in msg_lower:
        return (
            "TON uses a unique asynchronous model for smart contracts, written in two main languages:\n\n"
            "• **Tact**: A modern, developer-friendly language with strong typing and compile-time safety checks.\n"
            "• **FunC**: A lower-level, C-like language that offers maximum optimization and TVM access.\n\n"
            "Unlike Ethereum, TON smart contracts communicate via asynchronous messages rather than direct calls."
        )
    elif "sharding" in msg_lower or "shard" in msg_lower or "scaling" in msg_lower:
        return (
            "**Dynamic Sharding** is one of the core architectural features of the TON Blockchain:\n\n"
            "• **Dynamic Split & Merge**: Shardchains automatically split into two when transaction load increases, "
            "and merge back together when load drops, avoiding network congestion.\n"
            "• **Parallel Processing**: Each shardchain executes transactions in parallel, allowing massive horizontal scaling.\n"
            "• **Masterchain Coordination**: The Masterchain maintains block parameters and validator coordinates to route messages between shards."
        )
    else:
        return (
            "I'm here to help you learn about TON! Currently, the OpenAI AI API is not configured or unavailable, "
            "but I can answer questions about:\n\n"
            "• **What is TON?**\n"
            "• **What is Toncoin?**\n"
            "• **What wallets are available?**\n"
            "• **How to write smart contracts?**\n\n"
            "Please configure a valid `OPENAI_API_KEY` in your `env/key.env` file for unrestricted AI chat."
        )

# -------------------------------
# Telegram Bot Handlers
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    log_event(f"Telegram Bot: User {username} started the bot (/start).", "info")
    
    await update.message.reply_text(
        "Hi, welcome to the TON Africa Telegram Bot. "
        "This bot is designed to educate you about TON and provide useful information automatically."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when /help is issued."""
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    log_event(f"Telegram Bot: User {username} requested help (/help).", "info")
    
    await update.message.reply_text(
        "📚 Available Commands:\n"
        "/start - Start the bot and see the welcome message\n"
        "/help - Show this help message\n"
        "You can also send messages and I will respond to TON-related questions!"
    )

async def ton_qa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Answer TON-related questions with OpenAI AI (grounded by context) or local fallback."""
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    user_msg = update.message.text.strip()
    
    log_event(f"Telegram Bot: Message from {username}: '{user_msg}'", "info")
    
    if not openai_configured or not openai_client:
        log_event("Telegram Bot: OpenAI API is not configured. Using local fallback.", "warning")
        fallback_reply = get_ton_fallback_response(user_msg)
        await update.message.reply_text(f"⚠️ (OpenAI AI not configured - Showing Fallback)\n\n" + fallback_reply)
        return

    # Only handle TON-related questions
    if "ton" in user_msg.lower() or "blockchain" in user_msg.lower():
        try:
            log_event(f"Telegram Bot: Querying OpenAI API (Managed Prompt) for '{username}'...", "info")
            try:
                # Call OpenAI Managed Prompt responses API
                response = await openai_client.responses.create(
                    prompt={
                        "id": "pmpt_6a12518928a4819598acc858c283a8540b5219277297c774",
                        "version": "1"
                    },
                    input=user_msg,
                    timeout=15
                )
                answer = response.output_text
                log_event(f"Telegram Bot: Answered question for {username} via OpenAI Managed Prompt.", "success")
            except Exception as pe:
                log_event(f"Telegram Bot: Managed Prompt call failed ({pe}). Falling back to completions...", "warning")
                # Fallback to chat completions
                response = await openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg}
                    ],
                    timeout=15
                )
                answer = response.choices[0].message.content
                log_event(f"Telegram Bot: Answered question for {username} via OpenAI Chat Completions fallback.", "success")
        except Exception as e:
            log_event(f"Telegram Bot: OpenAI API error: {e}. Using local fallback.", "error")
            answer = f"⚠️ (OpenAI API error - Showing Fallback)\n\n" + get_ton_fallback_response(user_msg)

        await update.message.reply_text(answer)
    else:
        log_event(f"Telegram Bot: Sent generic guide response to {username}.", "info")
        await update.message.reply_text(
            "🤖 I specialize in TON Blockchain questions. Try asking about TON, Toncoin, wallets, staking, NFTs, or smart contracts."
        )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check uploaded images using Pillow."""
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    log_event(f"Telegram Bot: Received photo from {username}.", "info")
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    try:
        # Get the last photo from the message
        photo_file = await update.message.photo[-1].get_file()
        file_path = f"downloads/{photo_file.file_id}.jpg"

        # Download the image
        await photo_file.download_to_drive(file_path)
        log_event(f"Telegram Bot: Photo downloaded to {file_path}", "info")

        # Detect image type using Pillow
        with Image.open(file_path) as img:
            img_type = img.format
            img_size = img.size
            
        log_event(f"Telegram Bot: Image verified successfully (Format: {img_type}, Size: {img_size[0]}x{img_size[1]})", "success")
        await update.message.reply_text(f"✅ Image received and verified as {img_type} ({img_size[0]}x{img_size[1]}).")
    except Exception as e:
        log_event(f"Telegram Bot: Image processing failed: {e}", "error")
        await update.message.reply_text("⚠️ Uploaded file is not a valid image.")

# -------------------------------
# FastAPI Application & Lifecycle
# -------------------------------
bot_app = None
bot_active = False
openai_client = None
openai_configured = False
system_prompt = ""

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_app, bot_active, openai_client, openai_configured, system_prompt
    log_event("Initializing TON Africa educational system server...", "system")
    
    # 1. Load TON Knowledge Base Feed
    ton_knowledge = ""
    try:
        if os.path.exists("ton_knowledge.txt"):
            with open("ton_knowledge.txt", "r", encoding="utf-8") as f:
                ton_knowledge = f.read()
            log_event("TON knowledge base loaded successfully from ton_knowledge.txt.", "success")
        else:
            log_event("Warning: ton_knowledge.txt not found. Using default instructions.", "warning")
            ton_knowledge = "TON (The Open Network) is a dynamic-sharded layer-1 blockchain."
    except Exception as e:
        log_event(f"Error loading ton_knowledge.txt: {e}", "error")
        ton_knowledge = "TON (The Open Network) is a dynamic-sharded layer-1 blockchain."

    system_prompt = (
        "You are a helpful, expert AI assistant specializing in the TON (The Open Network) Blockchain. "
        "Use the following official TON knowledge base reference documentation to answer user questions accurately. "
        "Your answers should be extremely precise and directly grounded in the provided reference material. "
        "If a question is completely unrelated to TON (e.g. asking about recipes, unrelated cryptocurrencies, or generic coding advice), "
        "you must politely remind the user that your expertise is strictly limited to the TON blockchain ecosystem.\n\n"
        f"--- TON OFFICIAL REFERENCE MANUAL ---\n{ton_knowledge}\n-------------------------------------\n\n"
        "Format your responses cleanly using markdown (with bold text, subheaders, and bullet lists where appropriate)."
    )

    # 2. Configure OpenAI API Client
    if OPENAI_API_KEY:
        try:
            openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            openai_configured = True
            log_event("OpenAI AI API client initialized successfully.", "success")
        except Exception as e:
            openai_configured = False
            log_event(f"OpenAI configuration error: {e}", "error")
    else:
        openai_configured = False
        log_event("OPENAI_API_KEY is missing. AI chat will run in local fallback mode.", "warning")

    # 3. Start Telegram Bot
    if TOKEN:
        try:
            log_event("Starting Telegram bot polling task...", "system")
            # Build the bot application
            bot_app = ApplicationBuilder().token(TOKEN).build()

            # Add handlers
            bot_app.add_handler(CommandHandler("start", start))
            bot_app.add_handler(CommandHandler("help", help_command))
            bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), ton_qa))
            bot_app.add_handler(MessageHandler(filters.PHOTO, handle_image))
            
            # Clear webhook to avoid polling conflict
            try:
                await bot_app.bot.delete_webhook()
                log_event("Webhook cleared successfully.", "success")
            except Exception as e:
                log_event(f"Webhook deletion warning: {e}", "warning")

            # Initialize and start polling
            await bot_app.initialize()
            await bot_app.start()
            await bot_app.updater.start_polling()
            bot_active = True
            log_event("Telegram Bot is running concurrently in the background.", "success")
        except Exception as e:
            bot_active = False
            log_event(f"Failed to start Telegram Bot polling: {e}", "error")
    else:
        bot_active = False
        log_event("BOT_TOKEN is missing. Telegram bot is disabled.", "warning")

    yield

    # Shutdown logic
    if bot_app:
        log_event("Shutting down Telegram bot polling...", "system")
        try:
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()
            log_event("Telegram bot stopped.", "success")
        except Exception as e:
            log_event(f"Error during bot shutdown: {e}", "error")

app = FastAPI(
    title="TON Africa Educational Portal API",
    lifespan=lifespan
)

# CORS Policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Request Schema
# -------------------------------
class ChatRequest(BaseModel):
    message: str

# -------------------------------
# API Endpoints
# -------------------------------

@app.post("/api/chat")
async def api_chat(payload: ChatRequest):
    """Q&A endpoint for the web dashboard powered by OpenAI AI (grounded by context)."""
    user_msg = payload.message.strip()
    log_event(f"Web API: Chat request received: '{user_msg}'", "info")
    
    if not openai_configured or not openai_client:
        log_event("Web API: OpenAI API is not configured. Using local fallback.", "warning")
        fallback_reply = get_ton_fallback_response(user_msg)
        return {"reply": f"⚠️ *Note: The OpenAI API Key is not configured. Showing a local educational response:* \n\n{fallback_reply}"}
        
    try:
        log_event(f"Web API: Querying OpenAI API (Managed Prompt) for user query...", "info")
        try:
            # Call OpenAI Managed Prompt responses API
            response = await openai_client.responses.create(
                prompt={
                    "id": "pmpt_6a12518928a4819598acc858c283a8540b5219277297c774",
                    "version": "1"
                },
                input=user_msg,
                timeout=15
            )
            answer = response.output_text
            log_event("Web API: Sent OpenAI Managed Prompt reply back to client.", "success")
            return {"reply": answer}
        except Exception as pe:
            log_event(f"Web API: Managed Prompt call failed ({pe}). Falling back to completions...", "warning")
            # Fallback to chat completions
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                timeout=15
            )
            answer = response.choices[0].message.content
            log_event("Web API: Sent OpenAI Chat Completions fallback reply back to client.", "success")
            return {"reply": answer}

    except Exception as e:
        log_event(f"Web API: OpenAI server call failed: {e}. Using local fallback.", "error")
        fallback_reply = get_ton_fallback_response(user_msg)
        return {"reply": f"⚠️ *Note: Could not reach OpenAI AI server. Showing a local educational response:* \n\n{fallback_reply}"}

@app.post("/api/upload")
async def api_upload(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None)
):
    """Upload and process image metadata using Pillow, with optional AI chat guidance."""
    log_event(f"Web API: Received image upload '{file.filename}'", "info")
    
    try:
        # Read file bytes into memory
        file_bytes = await file.read()
        
        # Open and verify with Pillow
        img = Image.open(io.BytesIO(file_bytes))
        img_format = img.format
        img_size = img.size
        img_mode = img.mode
        
        log_event(f"Web API: Image '{file.filename}' verified (Format: {img_format}, Size: {img_size})", "success")
        
        # Optional: query AI about the image validation
        ai_response = ""
        if prompt:
            ai_response = f"Verified image format as {img_format} with mode {img_mode}. User note: '{prompt}'"
            
        return {
            "filename": file.filename,
            "format": img_format,
            "size": img_size,
            "mode": img_mode,
            "ai_response": ai_response
        }
        
    except Exception as e:
        log_event(f"Web API: Pillow image verification failed: {e}", "error")
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")

@app.get("/api/status")
async def api_status():
    """Get Telegram Bot connectivity state and system telemetry."""
    return {
        "bot_active": bot_active,
        "credentials": {
            "BOT_TOKEN": "configured" if TOKEN else "missing",
            "OPENAI_API_KEY": "configured" if OPENAI_API_KEY else "missing"
        },
        "logs": system_logs
    }

# -------------------------------
# Static Frontend Serving
# -------------------------------
# Check if frontend folder exists, and serve it
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
else:
    log_event("Frontend folder was not found. API endpoints are running, but web pages are disabled.", "warning")

# -------------------------------
# Main runner
# -------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    log_event(f"Starting server.py on http://0.0.0.0:{port}...", "system")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
