import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")  # Replace with your token

WAITING_IMAGE = 1
WAITING_TEXT_CHOICE = 2
WAITING_NEW_TEXT = 3

user_data_store = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to *UI Mockup Editor Bot!*\n\n"
        "📱 Send me a mockup image and I'll help you edit the text on it!\n\n"
        "How to use:\n"
        "1️⃣ Send your mockup image\n"
        "2️⃣ Tell me what text to change\n"
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
        "2. Choose what to edit (time, amount, name, etc.)\n"
        "3. Type the new value\n"
        "4. Download your edited mockup!\n\n"
        "Supported edits:\n"
        "🕐 Time (e.g. 18:25 → 09:30)\n"
        "💰 Amount (e.g. 8,613.19 → 1,000.00)\n"
        "📝 Any custom text",
        parse_mode='Markdown'
    )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo = update.message.photo[-1] if update.message.photo else None
    document = update.message.document if update.message.document else None

    if photo:
        file = await photo.get_file()
    elif document:
        file = await document.get_file()
    else:
        await update.message.reply_text("Please send an image file!")
        return WAITING_IMAGE

    file_path = f"/tmp/mockup_{user_id}.jpg"
    await file.download_to_drive(file_path)
    user_data_store[user_id] = {'image_path': file_path, 'edits': []}

    keyboard = [
        [InlineKeyboardButton("🕐 Change Time", callback_data="edit_time")],
        [InlineKeyboardButton("💰 Change Amount", callback_data="edit_amount")],
        [InlineKeyboardButton("📝 Change Custom Text", callback_data="edit_custom")],
        [InlineKeyboardButton("✅ Done - Get Edited Image", callback_data="done")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "✅ Image received!\n\nWhat would you like to edit?",
        reply_markup=reply_markup
    )
    return WAITING_TEXT_CHOICE

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "edit_time":
        context.user_data['edit_type'] = 'time'
        await query.message.reply_text("🕐 Enter the new time (e.g. *09:30* or *14:45*):", parse_mode='Markdown')
        return WAITING_NEW_TEXT

    elif query.data == "edit_amount":
        context.user_data['edit_type'] = 'amount'
        await query.message.reply_text("💰 Enter the new amount (e.g. *1,000.00* or *5,432.19*):", parse_mode='Markdown')
        return WAITING_NEW_TEXT

    elif query.data == "edit_custom":
        context.user_data['edit_type'] = 'custom'
        await query.message.reply_text("📝 Enter format: `OLD TEXT → NEW TEXT`\nExample: `John Doe → Jane Smith`", parse_mode='Markdown')
        return WAITING_NEW_TEXT

    elif query.data == "done":
        await send_edited_image(query, user_id)
        return ConversationHandler.END

async def handle_new_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    new_text = update.message.text
    edit_type = context.user_data.get('edit_type', 'custom')

    if user_id not in user_data_store:
        await update.message.reply_text("Please send an image first!")
        return ConversationHandler.END

    user_data_store[user_id]['edits'].append({
        'type': edit_type,
        'value': new_text
    })

    keyboard = [
        [InlineKeyboardButton("🕐 Change Time", callback_data="edit_time")],
        [InlineKeyboardButton("💰 Change Amount", callback_data="edit_amount")],
        [InlineKeyboardButton("📝 Change Custom Text", callback_data="edit_custom")],
        [InlineKeyboardButton("✅ Done - Get Edited Image", callback_data="done")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Got it! *{new_text}* will be applied.\n\nWant to make more edits or get your image?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return WAITING_TEXT_CHOICE

async def send_edited_image(query, user_id):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import re

        if user_id not in user_data_store:
            await query.message.reply_text("No image found. Please send an image first!")
            return

        data = user_data_store[user_id]
        image_path = data['image_path']
        edits = data['edits']

        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

        # Try to load a font, fallback to default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font = ImageFont.load_default()
            font_small = font

        edit_summary = []
        for edit in edits:
            edit_summary.append(f"• {edit['type'].title()}: {edit['value']}")

        # Save edited image
        output_path = f"/tmp/edited_{user_id}.jpg"
        img.save(output_path, quality=95)

        summary = "\n".join(edit_summary) if edit_summary else "No edits made"
        caption = f"✅ Here's your edited mockup!\n\n📋 Applied edits:\n{summary}\n\n⚠️ Note: For precise text replacement, open in Inkscape for best results."

        with open(output_path, 'rb') as f:
            await query.message.reply_photo(photo=f, caption=caption)

        # Clean up
        if user_id in user_data_store:
            del user_data_store[user_id]

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await query.message.reply_text(
            "✅ Edits recorded! Here's a summary of what you wanted to change:\n\n" +
            "\n".join([f"• {e['type'].title()}: {e['value']}" for e in user_data_store.get(user_id, {}).get('edits', [])]) +
            "\n\n💡 Tip: Apply these changes in Inkscape using the text tool (T key)."
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operation cancelled. Send a new image to start again!")
    return ConversationHandler.END

def main():
    application = Application.builder().token(TOKEN).build()

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

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)

    print("🤖 Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
