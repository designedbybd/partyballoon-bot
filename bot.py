"""
Party Balloon Logo Bot
bout telegram le-izafet el-logo 3ala el-sowar w el-videohat
"""
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import io
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from logo_processor import add_logo_to_image, generate_white_logo_from_black
from video_processor import add_logo_to_video, VideoProcessingError
from config import BOT_TOKEN, CHANNEL_ID

# ─── إعداد اللوج ───────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── مفاتيح تخزين البيانات المؤقتة ──────────────────────────────
KEY_ITEMS = "batch_items"          # [{"type": "photo"/"video", "bytes": b}, ...]
KEY_COLOR = "selected_color"
KEY_PROMPT_MSG_ID = "prompt_message_id"

MAX_BATCH_SIZE = 20  # حد أقصى تحوطي لعدد العناصر في الدفعة الواحدة

POSITION_LABELS = {
    "top_right":     "↗ يمين فوق",
    "top_left":      "↖ شمال فوق",
    "bottom_right":  "↘ يمين تحت",
    "bottom_left":   "↙ شمال تحت",
    "top_center":    "⬆ نص فوق",
    "bottom_center": "⬇ نص تحت",
}


# ════════════════════════════════════════════════════════════════
# /start
# ════════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎈 *أهلاً بك في Party Balloon Bot!*\n\n"
        "ابعت صورة أو فيديو (أو أكتر من واحد مع بعض) وأنا هضيف اللوجو عليهم ✨\n\n"
        "ابعت العناصر اللي عايزها، وبعدين اختر اللون والموضع، وأنا هعالجهم كلهم وأبعتهم لك وللقناة 👇",
        parse_mode="Markdown"
    )


# ════════════════════════════════════════════════════════════════
# استقبال صورة أو فيديو → إضافة للدفعة الحالية
# ════════════════════════════════════════════════════════════════
async def _add_item_to_batch(update: Update, context: ContextTypes.DEFAULT_TYPE, item_type: str, item_bytes: bytes):
    items = context.user_data.setdefault(KEY_ITEMS, [])

    if len(items) >= MAX_BATCH_SIZE:
        await update.message.reply_text(
            f"⚠️ وصلت للحد الأقصى ({MAX_BATCH_SIZE} عنصر) في الدفعة الواحدة.\n"
            "اختر اللون دلوقتي عشان نكمل، أو ابعت /cancel لإلغاء الدفعة."
        )
        return

    items.append({"type": item_type, "bytes": item_bytes})
    count = len(items)
    photos_count = sum(1 for i in items if i["type"] == "photo")
    videos_count = sum(1 for i in items if i["type"] == "video")

    parts = []
    if photos_count:
        parts.append(f"{photos_count} صورة")
    if videos_count:
        parts.append(f"{videos_count} فيديو")
    summary = " و".join(parts)

    text = (
        f"📥 تم استلام {summary} (إجمالي {count}).\n"
        "ابعت عناصر تانية لو عايز، أو اختر لون اللوجو للمتابعة 👇\n\n"
        "🎨 اختر لون اللوجو:"
    )

    keyboard = [
        [
            InlineKeyboardButton("⚫ أسود", callback_data="color_black"),
            InlineKeyboardButton("⚪ أبيض", callback_data="color_white"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    prompt_msg_id = context.user_data.get(KEY_PROMPT_MSG_ID)
    if prompt_msg_id:
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=prompt_msg_id,
                text=text,
                reply_markup=reply_markup,
            )
            return
        except BadRequest:
            pass  # الرسالة القديمة اتشالت أو مش قابلة للتعديل، هنبعت وحدة جديدة

    msg = await update.message.reply_text(text, reply_markup=reply_markup)
    context.user_data[KEY_PROMPT_MSG_ID] = msg.message_id


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]  # أعلى جودة
    file = await photo.get_file()
    photo_bytes = await file.download_as_bytearray()
    await _add_item_to_batch(update, context, "photo", bytes(photo_bytes))


async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    try:
        file = await video.get_file()
        video_bytes = await file.download_as_bytearray()
    except Exception as e:
        logger.error(f"خطأ في تحميل الفيديو: {e}")
        await update.message.reply_text(
            "❌ مقدرتش أحمّل الفيديو ده (ممكن يكون كبير أوي). جرّب فيديو أصغر."
        )
        return
    await _add_item_to_batch(update, context, "video", bytes(video_bytes))


# ════════════════════════════════════════════════════════════════
# اختيار اللون → طلب اختيار الموضع
# ════════════════════════════════════════════════════════════════
async def select_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not context.user_data.get(KEY_ITEMS):
        await query.edit_message_text("⚠️ مفيش صور أو فيديوهات محفوظة، ابعت عنصر الأول.")
        return

    color = query.data.replace("color_", "")  # "black" أو "white"
    context.user_data[KEY_COLOR] = color
    context.user_data.pop(KEY_PROMPT_MSG_ID, None)

    color_label = "⚫ أسود" if color == "black" else "⚪ أبيض"

    keyboard = [
        [
            InlineKeyboardButton("↖ شمال فوق",  callback_data="pos_top_left"),
            InlineKeyboardButton("↗ يمين فوق",  callback_data="pos_top_right"),
        ],
        [
            InlineKeyboardButton("⬆ نص فوق",   callback_data="pos_top_center"),
        ],
        [
            InlineKeyboardButton("↙ شمال تحت",  callback_data="pos_bottom_left"),
            InlineKeyboardButton("↘ يمين تحت",  callback_data="pos_bottom_right"),
        ],
        [
            InlineKeyboardButton("⬇ نص تحت",   callback_data="pos_bottom_center"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ اللون: {color_label}\n\n📍 اختر موضع اللوجو:",
        reply_markup=reply_markup
    )


# ════════════════════════════════════════════════════════════════
# إرسال النتايج (صورة/فيديو واحد، أو ألبوم لو أكتر من عنصر)
# ════════════════════════════════════════════════════════════════
async def _send_results(context: ContextTypes.DEFAULT_TYPE, chat_id, results, caption, parse_mode=None):
    """
    results: [{"type": "photo"/"video", "bytes": b}, ...]
    """
    if len(results) == 1:
        item = results[0]
        if item["type"] == "photo":
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=io.BytesIO(item["bytes"]),
                caption=caption,
                parse_mode=parse_mode,
            )
        else:
            await context.bot.send_video(
                chat_id=chat_id,
                video=io.BytesIO(item["bytes"]),
                caption=caption,
                parse_mode=parse_mode,
                supports_streaming=True,
            )
        return

    # أكتر من عنصر → إرسال كألبوم (Telegram بيسمح لغاية 10 عناصر في الألبوم الواحد)
    for i in range(0, len(results), 10):
        chunk = results[i:i + 10]
        media = []
        for idx, item in enumerate(chunk):
            item_caption = caption if (i == 0 and idx == 0) else None
            item_parse_mode = parse_mode if item_caption else None
            if item["type"] == "photo":
                media.append(InputMediaPhoto(
                    media=io.BytesIO(item["bytes"]),
                    caption=item_caption,
                    parse_mode=item_parse_mode,
                ))
            else:
                media.append(InputMediaVideo(
                    media=io.BytesIO(item["bytes"]),
                    caption=item_caption,
                    parse_mode=item_parse_mode,
                    supports_streaming=True,
                ))
        await context.bot.send_media_group(chat_id=chat_id, media=media)


# ════════════════════════════════════════════════════════════════
# اختيار الموضع → معالجة كل العناصر وإرسالها
# ════════════════════════════════════════════════════════════════
async def select_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    position = query.data.replace("pos_", "")  # "top_right" etc.
    color = context.user_data.get(KEY_COLOR, "black")
    items = context.user_data.get(KEY_ITEMS, [])

    if not items:
        await query.edit_message_text("⚠️ مفيش صور أو فيديوهات محفوظة، ابعت عنصر الأول.")
        context.user_data.clear()
        return

    color_label = "⚫ أسود" if color == "black" else "⚪ أبيض"
    position_label = POSITION_LABELS.get(position, position)
    count = len(items)
    photos_count = sum(1 for i in items if i["type"] == "photo")
    videos_count = sum(1 for i in items if i["type"] == "video")

    await query.edit_message_text(
        f"⏳ جاري معالجة {count} عنصر ({photos_count} صورة، {videos_count} فيديو)...\n"
        f"• اللون: {color_label}\n"
        f"• الموضع: {position_label}\n\n"
        f"الفيديوهات ممكن تاخد وقت أطول شوية 🎬"
    )

    results = []
    failed = 0

    for item in items:
        try:
            if item["type"] == "photo":
                result_bytes = add_logo_to_image(item["bytes"], color, position)
            else:
                result_bytes = add_logo_to_video(item["bytes"], color, position)
            results.append({"type": item["type"], "bytes": result_bytes})
        except VideoProcessingError as e:
            logger.error(f"خطأ في معالجة فيديو: {e}")
            failed += 1
        except Exception as e:
            logger.error(f"خطأ في معالجة عنصر: {e}")
            failed += 1

    if not results:
        await query.message.reply_text(
            "❌ حصل خطأ ومقدرتش أعالج أي عنصر. تأكد من الملفات وحاول تاني."
        )
        context.user_data.clear()
        return

    user_name = update.effective_user.first_name if update.effective_user else "مستخدم مجهول"
    ok_count = len(results)

    plural_note = f" ({ok_count} من {count})" if failed else ""
    user_caption = (
        f"✅ *تم!* اللوجو أُضيف بنجاح{plural_note} 🎈\n"
        f"• اللون: {color_label}\n"
        f"• الموضع: {position_label}\n\n"
        f"ابعت صورة أو فيديو جديد لو عايز تكمل 👇"
    )
    channel_caption = (
        f"👤 من: {user_name}\n"
        f"• اللون: {color_label}\n"
        f"• الموضع: {position_label}\n"
        f"• عدد العناصر: {ok_count}"
    )

    try:
        await _send_results(context, query.message.chat_id, results, user_caption, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"خطأ في إرسال النتيجة للمستخدم: {e}")
        await query.message.reply_text("❌ حصل خطأ أثناء إرسال النتيجة.")

    if CHANNEL_ID:
        try:
            await _send_results(context, CHANNEL_ID, results, channel_caption)
        except Exception as e:
            logger.error(f"خطأ في الإرسال للقناة: {e}")
            await query.message.reply_text(
                "⚠️ تمت معالجة العناصر لكن حصل خطأ أثناء إرسالها للقناة."
            )

    if failed:
        await query.message.reply_text(
            f"⚠️ {failed} عنصر فشلت معالجته ومتبعتش."
        )

    context.user_data.clear()


# ════════════════════════════════════════════════════════════════
# إلغاء / خروج
# ════════════════════════════════════════════════════════════════
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ تم الإلغاء. ابعت صور أو فيديوهات جديدة لما تجهز 🎈")


# ════════════════════════════════════════════════════════════════
# رسائل غير متوقعة
# ════════════════════════════════════════════════════════════════
async def unexpected_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎈 ابعتلي صورة أو فيديو وأنا هضيف عليهم اللوجو!\n"
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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(MessageHandler(filters.VIDEO, receive_video))
    app.add_handler(CallbackQueryHandler(select_color, pattern="^color_"))
    app.add_handler(CallbackQueryHandler(select_position, pattern="^pos_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unexpected_message))

    print("[OK] Bot is ready! Waiting for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
