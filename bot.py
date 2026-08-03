"""
Party Balloon Logo Bot
bout telegram le-izafet el-logo 3ala el-sowar w el-videohat
"""
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import io
import json
import logging
from urllib.parse import quote
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
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
from grid_builder import create_grid_story
from config import BOT_TOKEN, CHANNEL_ID, LOGO_SIZE_OPTIONS, MINI_APP_URL

# ─── إعداد اللوج ───────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── مفاتيح تخزين البيانات المؤقتة ──────────────────────────────
KEY_ITEMS = "batch_items"          # [{"type": "photo"/"video", "bytes": b, "preview_path": str|None}, ...]
KEY_COLOR = "selected_color"
KEY_SIZE = "selected_size"
KEY_PROMPT_MSG_ID = "prompt_message_id"
KEY_CUSTOM_XY = "custom_xy_ratio"   # (x_ratio, y_ratio) من المعاينة الحية
KEY_CUSTOM_SIZE = "custom_size_ratio"  # نسبة الحجم من المعاينة الحية

MAX_BATCH_SIZE = 20  # حد أقصى تحوطي لعدد العناصر في الدفعة الواحدة

SIZE_LABELS = {
    "small":  "🔹 صغير",
    "medium": "🔸 متوسط",
    "large":  "🔶 كبير",
    "xlarge": "🟠 أكبر",
}

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
        "ابعت العناصر اللي عايزها، وبعدين اختر اللون، وبعدها تقدر تحدد المكان والحجم يدوي بمعاينة حية 🎯 أو تختار من أزرار جاهزة ⚡، وأنا هعالجهم كلهم وأبعتهم لك وللقناة 👇",
        parse_mode="Markdown"
    )


# ════════════════════════════════════════════════════════════════
# استقبال صورة أو فيديو → إضافة للدفعة الحالية
# ════════════════════════════════════════════════════════════════
async def _add_item_to_batch(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_type: str,
    item_bytes: bytes,
    preview_path: str = None,
):
    items = context.user_data.setdefault(KEY_ITEMS, [])

    if len(items) >= MAX_BATCH_SIZE:
        await update.message.reply_text(
            f"⚠️ وصلت للحد الأقصى ({MAX_BATCH_SIZE} عنصر) في الدفعة الواحدة.\n"
            "اختر اللون دلوقتي عشان نكمل، أو ابعت /cancel لإلغاء الدفعة."
        )
        return

    items.append({"type": item_type, "bytes": item_bytes, "preview_path": preview_path})
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
    await _add_item_to_batch(update, context, "photo", bytes(photo_bytes), file.file_path)


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

    # صورة مصغّرة (thumbnail) بنستخدمها في المعاينة الحية (الفيديو نفسه مش قابل للعرض كـ <img>)
    preview_path = None
    if video.thumbnail:
        try:
            thumb_file = await video.thumbnail.get_file()
            preview_path = thumb_file.file_path
        except Exception as e:
            logger.warning(f"تعذّر تحميل صورة مصغّرة للفيديو: {e}")

    await _add_item_to_batch(update, context, "video", bytes(video_bytes), preview_path)


# ════════════════════════════════════════════════════════════════
# اختيار اللون → طلب اختيار طريقة تحديد الموضع (معاينة حية / اختيار سريع)
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
    context.user_data.pop(KEY_CUSTOM_XY, None)
    context.user_data.pop(KEY_CUSTOM_SIZE, None)

    color_label = "⚫ أسود" if color == "black" else "⚪ أبيض"
    photos_count = sum(1 for i in context.user_data.get(KEY_ITEMS, []) if i["type"] == "photo")

    keyboard = [
        [InlineKeyboardButton("🎯 معاينة حية (تحكم يدوي)", callback_data="mode_live")],
        [InlineKeyboardButton("⚡ اختيار سريع (أزرار جاهزة)", callback_data="mode_quick")],
    ]
    if photos_count >= 2:
        keyboard.append(
            [InlineKeyboardButton("🧩 دمج الصور في جريد واحد (ستوري)", callback_data="mode_grid")]
        )
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ اللون: {color_label}\n\n"
        f"تحب تحدد مكان وحجم اللوجو إزاي؟",
        reply_markup=reply_markup
    )


# ════════════════════════════════════════════════════════════════
# اختيار طريقة التحديد
# ════════════════════════════════════════════════════════════════
async def _show_size_keyboard(query, context: ContextTypes.DEFAULT_TYPE):
    color = context.user_data.get(KEY_COLOR, "black")
    color_label = "⚫ أسود" if color == "black" else "⚪ أبيض"

    keyboard = [
        [
            InlineKeyboardButton(SIZE_LABELS["small"],  callback_data="size_small"),
            InlineKeyboardButton(SIZE_LABELS["medium"], callback_data="size_medium"),
        ],
        [
            InlineKeyboardButton(SIZE_LABELS["large"],  callback_data="size_large"),
            InlineKeyboardButton(SIZE_LABELS["xlarge"], callback_data="size_xlarge"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ اللون: {color_label}\n\n📏 اختر مقاس اللوجو:",
        reply_markup=reply_markup
    )


async def select_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    items = context.user_data.get(KEY_ITEMS, [])
    if not items:
        await query.edit_message_text("⚠️ مفيش صور أو فيديوهات محفوظة، ابعت عنصر الأول.")
        return

    mode = query.data.replace("mode_", "")  # "live" / "quick" / "grid"

    if mode == "quick":
        await _show_size_keyboard(query, context)
        return

    if mode == "grid":
        await _process_grid(query, context, items)
        return

    # ─── معاينة حية ───
    if not MINI_APP_URL:
        await query.edit_message_text(
            "⚠️ المعاينة الحية مش متفعّلة على السيرفر لسه (لازم تتظبط أول مرة).\n"
            "هنكمل بالاختيار السريع بدلها 👇"
        )
        await _show_size_keyboard(query, context)
        return

    preview_item = next((i for i in items if i.get("preview_path")), None)
    if not preview_item:
        await query.edit_message_text(
            "⚠️ مقدرتش ألاقي صورة صالحة للمعاينة في الدفعة دي.\n"
            "هنكمل بالاختيار السريع بدلها 👇"
        )
        await _show_size_keyboard(query, context)
        return

    color = context.user_data.get(KEY_COLOR, "black")
    logo_filename = "logo_black.png" if color == "black" else "logo_white.png"

    photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{preview_item['preview_path']}"
    logo_url = f"{MINI_APP_URL.rstrip('/')}/assets/{logo_filename}"
    app_url = (
        f"{MINI_APP_URL.rstrip('/')}/"
        f"?photo={quote(photo_url, safe='')}"
        f"&logo={quote(logo_url, safe='')}"
        f"&size=0.22&pos=bottom_right"
    )

    await query.edit_message_text(
        "🎯 دوس الزرار تحت عشان تفتح شاشة المعاينة، اسحب اللوجو وحدد الحجم، وبعدين دوس تأكيد جوه الشاشة نفسها."
    )

    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("🖼 افتح المعاينة الحية", web_app=WebAppInfo(url=app_url))]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="👇 دوس هنا:",
        reply_markup=keyboard,
    )


# ════════════════════════════════════════════════════════════════
# دمج الصور في جريد واحد بمقاس الستوري
# ════════════════════════════════════════════════════════════════
async def _process_grid(query, context: ContextTypes.DEFAULT_TYPE, items):
    photos = [i["bytes"] for i in items if i["type"] == "photo"]
    videos_count = sum(1 for i in items if i["type"] == "video")

    if len(photos) < 2:
        await query.edit_message_text(
            "⚠️ محتاج صورتين على الأقل عشان أعمل جريد.\nهنكمل بالاختيار السريع بدلها 👇"
        )
        await _show_size_keyboard(query, context)
        return

    color = context.user_data.get(KEY_COLOR, "black")
    color_label = "⚫ أسود" if color == "black" else "⚪ أبيض"
    skip_note = f"\n(هيتجاهل {videos_count} فيديو، الجريد للصور بس)" if videos_count else ""

    await query.edit_message_text(
        f"⏳ جاري عمل جريد من {len(photos)} صورة بمقاس الستوري (1080×1920)...{skip_note}"
    )

    try:
        grid_bytes = create_grid_story(photos, color, LOGO_SIZE_OPTIONS["medium"])
    except Exception as e:
        logger.error(f"خطأ في عمل الجريد: {e}")
        await query.message.reply_text("❌ حصل خطأ أثناء عمل الجريد. جرب تاني.")
        context.user_data.clear()
        return

    user_name = query.from_user.first_name if query.from_user else "مستخدم مجهول"
    user_caption = (
        f"✅ *تم!* جريد من {len(photos)} صورة بمقاس الستوري 🎈\n"
        f"• اللون: {color_label}\n\n"
        f"ابعت صور جديدة لو عايز تكمل 👇"
    )
    channel_caption = (
        f"👤 من: {user_name}\n"
        f"• جريد {len(photos)} صور (ستوري 1080×1920)\n"
        f"• اللون: {color_label}"
    )

    result_item = [{"type": "photo", "bytes": grid_bytes}]

    try:
        await _send_results(context, query.message.chat_id, result_item, user_caption, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"خطأ في إرسال الجريد للمستخدم: {e}")
        await query.message.reply_text("❌ حصل خطأ أثناء إرسال الجريد.")

    if CHANNEL_ID:
        try:
            await _send_results(context, CHANNEL_ID, result_item, channel_caption)
        except Exception as e:
            logger.error(f"خطأ في إرسال الجريد للقناة: {e}")
            await query.message.reply_text("⚠️ تم عمل الجريد لكن حصل خطأ أثناء إرساله للقناة.")

    context.user_data.clear()


# ════════════════════════════════════════════════════════════════
# اختيار المقاس → طلب اختيار الموضع
# ════════════════════════════════════════════════════════════════
async def select_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not context.user_data.get(KEY_ITEMS):
        await query.edit_message_text("⚠️ مفيش صور أو فيديوهات محفوظة، ابعت عنصر الأول.")
        return

    size = query.data.replace("size_", "")  # "small" / "medium" / "large" / "xlarge"
    if size not in LOGO_SIZE_OPTIONS:
        size = "medium"
    context.user_data[KEY_SIZE] = size

    color = context.user_data.get(KEY_COLOR, "black")
    color_label = "⚫ أسود" if color == "black" else "⚪ أبيض"
    size_label = SIZE_LABELS.get(size, size)

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
        f"✅ اللون: {color_label}\n"
        f"✅ المقاس: {size_label}\n\n"
        f"📍 اختر موضع اللوجو:",
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
# معالجة دفعة العناصر (مشتركة بين الاختيار السريع والمعاينة الحية)
# ════════════════════════════════════════════════════════════════
async def _run_batch(items, color, size_ratio, position=None, custom_xy_ratio=None):
    """
    يعالج كل عنصر في الدفعة ويرجع (results, failed_count)
    """
    results = []
    failed = 0

    for item in items:
        try:
            if item["type"] == "photo":
                result_bytes = add_logo_to_image(
                    item["bytes"], color, position, size_ratio, custom_xy_ratio
                )
            else:
                result_bytes = add_logo_to_video(
                    item["bytes"], color, position, size_ratio, custom_xy_ratio
                )
            results.append({"type": item["type"], "bytes": result_bytes})
        except VideoProcessingError as e:
            logger.error(f"خطأ في معالجة فيديو: {e}")
            failed += 1
        except Exception as e:
            logger.error(f"خطأ في معالجة عنصر: {e}")
            failed += 1

    return results, failed


async def _finalize_batch(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id,
    user_first_name: str,
    results,
    failed: int,
    total_count: int,
    color_label: str,
    size_label: str,
    position_label: str,
    reply_to_on_error,
):
    """
    يبعت النتيجة النهائية للمستخدم وللقناة، وبيرجع بعد كده الحالة تتنضف
    """
    if not results:
        await reply_to_on_error(
            "❌ حصل خطأ ومقدرتش أعالج أي عنصر. تأكد من الملفات وحاول تاني."
        )
        return

    ok_count = len(results)
    plural_note = f" ({ok_count} من {total_count})" if failed else ""

    user_caption = (
        f"✅ *تم!* اللوجو أُضيف بنجاح{plural_note} 🎈\n"
        f"• اللون: {color_label}\n"
        f"• المقاس: {size_label}\n"
        f"• الموضع: {position_label}\n\n"
        f"ابعت صورة أو فيديو جديد لو عايز تكمل 👇"
    )
    channel_caption = (
        f"👤 من: {user_first_name}\n"
        f"• اللون: {color_label}\n"
        f"• المقاس: {size_label}\n"
        f"• الموضع: {position_label}\n"
        f"• عدد العناصر: {ok_count}"
    )

    try:
        await _send_results(context, chat_id, results, user_caption, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"خطأ في إرسال النتيجة للمستخدم: {e}")
        await reply_to_on_error("❌ حصل خطأ أثناء إرسال النتيجة.")

    if CHANNEL_ID:
        try:
            await _send_results(context, CHANNEL_ID, results, channel_caption)
        except Exception as e:
            logger.error(f"خطأ في الإرسال للقناة: {e}")
            await reply_to_on_error("⚠️ تمت معالجة العناصر لكن حصل خطأ أثناء إرسالها للقناة.")

    if failed:
        await reply_to_on_error(f"⚠️ {failed} عنصر فشلت معالجته ومتبعتش.")


# ════════════════════════════════════════════════════════════════
# اختيار الموضع (المسار السريع) → معالجة كل العناصر وإرسالها
# ════════════════════════════════════════════════════════════════
async def select_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    position = query.data.replace("pos_", "")  # "top_right" etc.
    color = context.user_data.get(KEY_COLOR, "black")
    size = context.user_data.get(KEY_SIZE, "medium")
    size_ratio = LOGO_SIZE_OPTIONS.get(size, LOGO_SIZE_OPTIONS["medium"])
    items = context.user_data.get(KEY_ITEMS, [])

    if not items:
        await query.edit_message_text("⚠️ مفيش صور أو فيديوهات محفوظة، ابعت عنصر الأول.")
        context.user_data.clear()
        return

    color_label = "⚫ أسود" if color == "black" else "⚪ أبيض"
    size_label = SIZE_LABELS.get(size, size)
    position_label = POSITION_LABELS.get(position, position)
    count = len(items)
    photos_count = sum(1 for i in items if i["type"] == "photo")
    videos_count = sum(1 for i in items if i["type"] == "video")

    await query.edit_message_text(
        f"⏳ جاري معالجة {count} عنصر ({photos_count} صورة، {videos_count} فيديو)...\n"
        f"• اللون: {color_label}\n"
        f"• المقاس: {size_label}\n"
        f"• الموضع: {position_label}\n\n"
        f"الفيديوهات ممكن تاخد وقت أطول شوية 🎬"
    )

    results, failed = await _run_batch(items, color, size_ratio, position=position)

    user_name = update.effective_user.first_name if update.effective_user else "مستخدم مجهول"

    async def reply_to_on_error(text):
        await query.message.reply_text(text)

    await _finalize_batch(
        context, query.message.chat_id, user_name, results, failed, count,
        color_label, size_label, position_label, reply_to_on_error,
    )

    context.user_data.clear()


# ════════════════════════════════════════════════════════════════
# استقبال بيانات المعاينة الحية (Mini App) → معالجة كل العناصر وإرسالها
# ════════════════════════════════════════════════════════════════
async def receive_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.message.web_app_data.data)
        x_ratio = float(data["x"])
        y_ratio = float(data["y"])
        size_ratio = float(data["size"])
    except Exception as e:
        logger.error(f"خطأ في قراءة بيانات المعاينة الحية: {e}")
        await update.message.reply_text(
            "⚠️ حصل خطأ في قراءة بيانات المعاينة. جرب تاني.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    color = context.user_data.get(KEY_COLOR, "black")
    items = context.user_data.get(KEY_ITEMS, [])

    if not items:
        await update.message.reply_text(
            "⚠️ مفيش صور أو فيديوهات محفوظة، ابعت عنصر الأول.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    color_label = "⚫ أسود" if color == "black" else "⚪ أبيض"
    size_label = f"📏 {round(size_ratio * 100)}% (معاينة حية)"
    position_label = "🎯 حسب اختيارك (معاينة حية)"
    count = len(items)
    photos_count = sum(1 for i in items if i["type"] == "photo")
    videos_count = sum(1 for i in items if i["type"] == "video")

    status_msg = await update.message.reply_text(
        f"⏳ جاري معالجة {count} عنصر ({photos_count} صورة، {videos_count} فيديو)...\n"
        f"• اللون: {color_label}\n"
        f"• {size_label}\n"
        f"• {position_label}\n\n"
        f"الفيديوهات ممكن تاخد وقت أطول شوية 🎬",
        reply_markup=ReplyKeyboardRemove(),
    )

    results, failed = await _run_batch(
        items, color, size_ratio, custom_xy_ratio=(x_ratio, y_ratio)
    )

    user_name = update.effective_user.first_name if update.effective_user else "مستخدم مجهول"

    async def reply_to_on_error(text):
        await context.bot.send_message(chat_id=status_msg.chat_id, text=text)

    await _finalize_batch(
        context, status_msg.chat_id, user_name, results, failed, count,
        color_label, size_label, position_label, reply_to_on_error,
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
    app.add_handler(CallbackQueryHandler(select_mode, pattern="^mode_"))
    app.add_handler(CallbackQueryHandler(select_size, pattern="^size_"))
    app.add_handler(CallbackQueryHandler(select_position, pattern="^pos_"))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, receive_web_app_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unexpected_message))

    print("[OK] Bot is ready! Waiting for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main() 
