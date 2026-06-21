import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")

WAITING_IMAGE = 1
WAITING_TEXT_CHOICE = 2
WAITING_NEW_TEXT = 3

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to *UI Mockup Editor Bot!*\n\n"
        "📱 Send me a mockup image and I'll help you edit it!\n\n"
        "1️⃣ Send your mockup image\n"
        "2️⃣ Choose what to edit\n"
        "3️⃣ Type the new text\n"
        "4️⃣ Get your edited mockup back!\n\n"
        "Send me an image to get started! 🚀",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 *UI Mockup Editor - Help*\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/cancel - Cancel current operation\n\n"
        "Steps:\n"
        "1. Send your mockup image\n"
        "2. Choose what to edit\n"
        "3. Type the new value\n"
        "4. Download your edited mockup!",
        parse_mode='Markdown'
    )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1] if update.message.photo else None
    document = update.message.document if update.message.document else None

    if photo:
        file = await photo.get_file()
    elif document:
        file = await document.get_file()
    else:
        await update.message.reply_text("Please send an image file!")
        return WAITING_IMAGE

    user_id = update.message.from_user.id
    file_path = f"/tmp/mockup_{user_id}.jpg"
    await file.download_to_drive(file_path)
    context.user_data['image_path'] = file_path
    context.user_data['edits'] = []

    keyboard = [
        [InlineKeyboardButton("🕐 Change Time", callback_data="edit_time")],
        [InlineKeyboardButton("💰 Change Amount", callback_data="edit_amount")],
        [InlineKeyboardButton("📝 Change Custom Text", callback_data="edit_custom")],
        [InlineKeyboardButton("✅ Done - Get Image", callback_data="done")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("✅ Image received! What would you like to edit?", reply_markup=reply_markup)
    return WAITING_TEXT_CHOICE

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "edit_time":
        context.user_data['edit_type'] = 'time'
        await query.message.reply_text("🕐 Enter the new time (e.g. *09:30*):", parse_mode='Markdown')
        return WAITING_NEW_TEXT

    elif query.data == "edit_amount":
        context.user_data['edit_type'] = 'amount'
        await query.message.reply_text("💰 Enter the new amount (e.g. *1,000.00*):", parse_mode='Markdown')
        return WAITING_NEW_TEXT

    elif query.data == "edit_custom":
        context.user_data['edit_type'] = 'custom'
        await query.message.reply_text("📝 Type your new text:", parse_mode='Markdown')
        return WAITING_NEW_TEXT

    elif query.data == "done":
        edits = context.user_data.get('edits', [])
        summary = "\n".join([f"• {e['type'].title()}: {e['value']}" for e in edits]) if edits else "No edits recorded"
        image_path = context.user_data.get('image_path')

        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                await query.message.reply_photo(
                    photo=f,
                    caption=f"✅ Here is your mockup!\n\n📋 Requested edits:\n{summary}\n\n💡 Apply these changes in Inkscape using the text tool (T key)."
                )
        else:
            await query.message.reply_text(f"📋 Requested edits:\n{summary}")
        return ConversationHandler.END

async def handle_new_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_text = update.message.text
    edit_type = context.user_data.get('edit_type', 'custom')

    if 'edits' not in context.user_data:
        context.user_data['edits'] = []

    context.user_data['edits'].append({'type': edit_type, 'value': new_text})

    keyboard = [
        [InlineKeyboardButton("🕐 Change Time", callback_data="edit_time")],
        [InlineKeyboardButton("💰 Change Amount", callback_data="edit_amount")],
        [InlineKeyboardButton("📝 Change Custom Text", callback_data="edit_custom")],
        [InlineKeyboardButton("✅ Done - Get Image", callback_data="done")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"✅ Got it! Want to make more edits?",
        reply_markup=reply_markup
    )
    return WAITING_TEXT_CHOICE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled. Send a new image to start again!")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image)],
        states={
            WAITING_TEXT_CHOICE: [CallbackQueryHandler(button_handler)],
            WAITING_NEW_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_text),
                CallbackQueryHandler(button_handler)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)

    print("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
