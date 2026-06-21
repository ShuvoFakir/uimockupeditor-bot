import logging
import os
import requests
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

WAITING_IMAGE = 1
WAITING_INSTRUCTION = 2

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to *UI Mockup Editor Bot!* (AI Powered)\n\n"
        "📱 Send me a mockup image and tell me what to change!\n\n"
        "Example instructions:\n"
        "• 'Change the time to 09:30'\n"
        "• 'Change the balance to 5,000 USDT'\n"
        "• 'What text is on this image?'\n"
        "• 'Describe this mockup'\n\n"
        "Send me an image to get started! 🚀",
        parse_mode='Markdown'
    )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1] if update.message.photo else None
    document = update.message.document if update.message.document else None
    caption = update.message.caption

    if photo:
        file = await photo.get_file()
    elif document:
        file = await document.get_file()
    else:
        await update.message.reply_text("Please send an image!")
        return WAITING_IMAGE

    user_id = update.message.from_user.id
    file_path = f"/tmp/mockup_{user_id}.jpg"
    await file.download_to_drive(file_path)
    context.user_data['image_path'] = file_path

    if caption:
        await update.message.reply_text("🤖 Analyzing your image with AI...")
        await analyze_image(update, context, caption, file_path)
        return ConversationHandler.END
    else:
        keyboard = [
            [InlineKeyboardButton("📝 Read all text", callback_data="read_text")],
            [InlineKeyboardButton("🔍 Describe the mockup", callback_data="describe")],
            [InlineKeyboardButton("✏️ I'll type my instruction", callback_data="custom")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "✅ Image received! What would you like to do?",
            reply_markup=reply_markup
        )
        return WAITING_INSTRUCTION

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    image_path = context.user_data.get('image_path')

    if query.data == "read_text":
        await query.message.reply_text("🤖 Reading all text from your image...")
        await analyze_image_from_query(query, image_path, "Please read and list ALL text visible in this image exactly as it appears.")
        return ConversationHandler.END

    elif query.data == "describe":
        await query.message.reply_text("🤖 Analyzing your mockup...")
        await analyze_image_from_query(query, image_path, "Describe this UI mockup in detail. List all visible elements, text, buttons, and layout.")
        return ConversationHandler.END

    elif query.data == "custom":
        await query.message.reply_text("✏️ Type your instruction (e.g. 'What is the balance shown?' or 'List all the text on screen'):")
        return WAITING_INSTRUCTION

async def handle_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instruction = update.message.text
    image_path = context.user_data.get('image_path')

    if not image_path:
        await update.message.reply_text("Please send an image first!")
        return ConversationHandler.END

    await update.message.reply_text("🤖 AI is analyzing your image...")
    await analyze_image(update, context, instruction, image_path)
    return ConversationHandler.END

async def analyze_image(update, context, instruction, image_path):
    try:
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        payload = {
            "contents": [{
                "parts": [
                    {"text": f"You are a UI design assistant. The user has sent a mockup image and wants help with it. User instruction: {instruction}\n\nPlease analyze the image and provide helpful information. If they want to change text, tell them exactly what text you see and where it is, and what it should be changed to."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
                ]
            }]
        }

        response = requests.post(GEMINI_URL, json=payload, timeout=30)
        result = response.json()

        if 'candidates' in result:
            ai_response = result['candidates'][0]['content']['parts'][0]['text']
            await update.message.reply_text(f"🤖 *AI Analysis:*\n\n{ai_response}", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ AI could not analyze the image. Please try again.")

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Error analyzing image. Please try again.")

async def analyze_image_from_query(query, image_path, instruction):
    try:
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        payload = {
            "contents": [{
                "parts": [
                    {"text": instruction},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
                ]
            }]
        }

        response = requests.post(GEMINI_URL, json=payload, timeout=30)
        result = response.json()

        if 'candidates' in result:
            ai_response = result['candidates'][0]['content']['parts'][0]['text']
            await query.message.reply_text(f"🤖 *AI Analysis:*\n\n{ai_response}", parse_mode='Markdown')
        else:
            await query.message.reply_text("❌ AI could not analyze the image.")

    except Exception as e:
        logger.error(f"Error: {e}")
        await query.message.reply_text("❌ Error analyzing image. Please try again.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled. Send a new image to start again!")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 *UI Mockup Editor - Help*\n\n"
        "How to use:\n"
        "1. Send a mockup image\n"
        "2. Choose an option or type your instruction\n\n"
        "You can also send image with caption directly!\n"
        "Example: Send image + caption 'What time is shown?'\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/cancel - Cancel current operation",
        parse_mode='Markdown'
    )

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image)],
        states={
            WAITING_INSTRUCTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instruction),
                CallbackQueryHandler(button_handler)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)

    print("🤖 AI Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
