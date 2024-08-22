import asyncio
import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
from groq import Groq
import langsmith
from dotenv import load_dotenv
import nest_asyncio

nest_asyncio.apply()  # Apply nest_asyncio to avoid event loop issues

load_dotenv()  # Load environment variables from .env

# Initialize Flask app
app = Flask(__name__)

# Retrieve API keys from environment variables
GROQ_API_KEY = "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"
TELEGRAM_BOT_TOKEN = "6916139020:AAGtReUc6tIIa-Pkb8m0qWbcO5fFapFVQVQ"
LANGSMITH_API_KEY = "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"

# Validate the presence of API keys
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set.")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")
if not LANGSMITH_API_KEY:
    raise ValueError("LANGSMITH_API_KEY environment variable is not set.")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# Initialize Langsmith client
langsmith_client = langsmith.Client(api_key=LANGSMITH_API_KEY)

# Initialize Telegram bot application
application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Welcome! Send me a text, and I will generate metadata for it.')

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Send me a text, and I will generate metadata including titles, tags, and descriptions.')

# Function to generate metadata using GROQ
async def generate_metadata(prompt: str) -> str:
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f"Generate metadata including a title, tags, and a brief description for the following text: {prompt}",
                }
            ],
            model="llama3-8b-8192",  # Example model
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        langsmith_client.log_error("Metadata generation failed", error=str(e))
        return f"An error occurred: {e}"

# Message handler to process incoming messages and generate metadata
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text
    metadata = await generate_metadata(user_input)
    await update.message.reply_text(metadata)

    # Log message handling with Langsmith
    langsmith_client.log_event("Message handled", details={
        "user_id": update.message.from_user.id,
        "message_text": user_input,
        "metadata": metadata
    })

@app.route(f'https://api.telegram.org/bot6916139020:AAGtReUc6tIIa-Pkb8m0qWbcO5fFapFVQVQ/setWebhook?url=https://telbot-z0g7.onrender.com/6916139020:AAGtReUc6tIIa-Pkb8m0qWbcO5fFapFVQVQ
/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(), application.bot)
        asyncio.run(application.process_update(update))
        return 'ok'
    except Exception as e:
        langsmith_client.log_error("Webhook processing failed", error=str(e))
        return 'error', 500

async def main() -> None:
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Use run_polling instead of setting up a webhook
    await application.run_polling()

# Entry point for the script
if __name__ == '__main__':
    asyncio.run(main())
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))