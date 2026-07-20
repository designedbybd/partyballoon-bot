"""
Party Balloon Logo Bot
bout telegram le-izafet el-logo 3ala el-sowar
"""
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from logo_processor import add_logo_to_image, generate_white_logo_from_black
from config import BOT_TOKEN

# ─── إعداد اللوج ───────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── حالات المحادثة ──────────────────────────────────────────────
WAITING_FOR_COLOR = 1
WAITING_FOR_POSITION = 2

# ─── مفاتيح تخزين البيانات المؤقتة ──────────────────────────────
KEY_PHOTO = "photo_bytes"
KEY_COLOR = "selected_color"


# ════════════════════════════════════════════════════════════════
# /start
# ════════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎈 *أهلاً بك في Party Balloon Bot!*\n\n"
        "أرسل لي صورة وسأضيف اللوجو عليها بشكل احترافي ✨\n\n"
        "فقط ابعت الصورة وانا هتولى الباقي 👇",
        parse_mode="Markdown"
    )


# ════════════════════════════════════════════════════════════════
# استقبال الصورة → طلب اختيار اللون
# ════════════════════════════════════════════════════════════════
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]  # أعلى جودة
    file = await photo.get_file()
    photo_bytes = await file.download_as_bytearray()
    
    # حفظ الصورة مؤقتًا
    context.user_data[KEY_PHOTO] = bytes(photo_bytes)
    
    # إظهار أزرار اختيار اللون
    keyboard = [
        [
            InlineKeyboardButton("⚫ أسود", callback_data="color_black"),
            InlineKeyboardButton("⚪ أبيض", callback_data="color_white"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎨 اختر لون اللوجو:",
        reply_markup=reply_markup
    )
    return WAITING_FOR_COLOR


# ════════════════════════════════════════════════════════════════
# اختيار اللون → طلب اختيار الموضع
# ════════════════════════════════════════════════════════════════
async def select_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    color = query.data.replace("color_", "")  # "black" أو "white"
    context.user_data[KEY_COLOR] = color
    
    color_label = "⚫ أسود" if color == "black" else "⚪ أبيض"
    
    # إظهار أزرار اختيار الموضع
    keyboard = [
        [
            InlineKeyboardButton("↖ شمال فوق",  callback_data="pos_top_left"),
            InlineKeyboardButton("↗ يمين فوق",  callback_data="pos_top_right"),
        ],
        [
            InlineKeyboardButton("↙ شمال تحت",  callback_data="pos_bottom_left"),
            InlineKeyboardButton("↘ يمين تحت",  callback_data="pos_bottom_right"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ اللون: {color_label}\n\n📍 اختر موضع اللوجو:",
        reply_markup=reply_markup
    )
    return WAITING_FOR_POSITION


# ════════════════════════════════════════════════════════════════
# اختيار الموضع → معالجة الصورة وإرسالها
# ════════════════════════════════════════════════════════════════
async def select_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    position = query.data.replace("pos_", "")  # "top_right" etc.
    color = context.user_data.get(KEY_COLOR, "black")
    photo_bytes = context.user_data.get(KEY_PHOTO)
    
    position_labels = {
        "top_right":    "↗ يمين فوق",
        "top_left":     "↖ شمال فوق",
        "bottom_right": "↘ يمين تحت",
        "bottom_left":  "↙ شمال تحت",
    }
    color_label = "⚫ أسود" if color == "black" else "⚪ أبيض"
    
    await query.edit_message_text(
        f"⏳ جاري المعالجة...\n"
        f"• اللون: {color_label}\n"
        f"• الموضع: {position_labels.get(position, position)}"
    )
    
    try:
        # إضافة اللوجو
        result_bytes = add_logo_to_image(photo_bytes, color, position)
        
        # إرسال الصورة الجاهزة
        await query.message.reply_photo(
            photo=result_bytes,
            caption=(
                f"✅ *تم!* اللوجو أُضيف بنجاح 🎈\n"
                f"• اللون: {color_label}\n"
                f"• الموضع: {position_labels.get(position, position)}\n\n"
                f"ابعت صورة جديدة لو عايز تكمل 👇"
            ),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"خطأ في المعالجة: {e}")
        await query.message.reply_text(
            "❌ حصل خطأ أثناء المعالجة. تأكد من الصورة وحاول تاني."
        )
    
    # مسح البيانات المؤقتة
    context.user_data.clear()
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════
# إلغاء / خروج
# ════════════════════════════════════════════════════════════════
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ تم الإلغاء. ابعت صورة جديدة لما تجهز 🎈")
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════
# رسائل غير متوقعة
# ════════════════════════════════════════════════════════════════
async def unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎈 ابعتلي صورة وأنا هضيف عليها اللوجو!\n"
        "أو استخدم /start للبداية من جديد."
    )


# ════════════════════════════════════════════════════════════════
# تشغيل البوت
# ════════════════════════════════════════════════════════════════
def main():
    # إنشاء النسخة البيضاء من اللوجو تلقائيًا لو مش موجودة
    generate_white_logo_from_black()
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ خطأ: ضع توكن البوت في ملف .env أو في config.py")
        return
    
    print("[*] Party Balloon Bot starting...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ConversationHandler: photo -> color -> position -> result
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, receive_photo)],
        states={
            WAITING_FOR_COLOR: [
                CallbackQueryHandler(select_color, pattern="^color_"),
            ],
            WAITING_FOR_POSITION: [
                CallbackQueryHandler(select_position, pattern="^pos_"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
        per_message=False,
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unexpected_message))
    
    print("[OK] Bot is ready! Waiting for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
