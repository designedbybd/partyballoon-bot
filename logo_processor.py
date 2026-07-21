"""
معالجة الصور وإضافة اللوجو
Logo Processor - Party Balloon Bot
"""
from PIL import Image
import io
import os
from config import LOGO_BLACK_PATH, LOGO_WHITE_PATH, LOGO_SIZE_RATIO, LOGO_MARGIN


def prepare_logo(logo_path: str, target_width: int) -> Image.Image:
    """تحضير اللوجو بالحجم المناسب"""
    logo = Image.open(logo_path).convert("RGBA")
    
    # حساب الحجم الجديد مع الحفاظ على النسب
    logo_w = int(target_width * LOGO_SIZE_RATIO)
    ratio = logo_w / logo.width
    logo_h = int(logo.height * ratio)
    
    logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
    return logo


def get_logo_position(position: str, img_w: int, img_h: int, logo_w: int, logo_h: int) -> tuple:
    """حساب موضع اللوجو"""
    margin = LOGO_MARGIN
    
    positions = {
        "top_right":     (img_w - logo_w - margin, margin),
        "top_left":      (margin, margin),
        "bottom_right":  (img_w - logo_w - margin, img_h - logo_h - margin),
        "bottom_left":   (margin, img_h - logo_h - margin),
        "top_center":    ((img_w - logo_w) // 2, margin),
        "bottom_center": ((img_w - logo_w) // 2, img_h - logo_h - margin),
    }
    return positions.get(position, positions["bottom_right"])


def add_logo_to_image(
    image_bytes: bytes,
    color: str,
    position: str
) -> bytes:
    """
    إضافة اللوجو على الصورة
    
    Args:
        image_bytes: بيانات الصورة
        color: "black" أو "white"
        position: "top_right" / "top_left" / "bottom_right" / "bottom_left"
    
    Returns:
        بيانات الصورة بعد إضافة اللوجو (JPEG)
    """
    # فتح الصورة الأصلية
    image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    img_w, img_h = image.size

    # اختيار ملف اللوجو
    logo_path = LOGO_BLACK_PATH if color == "black" else LOGO_WHITE_PATH

    # تحضير اللوجو
    logo = prepare_logo(logo_path, img_w)
    logo_w, logo_h = logo.size

    # حساب الموضع
    x, y = get_logo_position(position, img_w, img_h, logo_w, logo_h)

    # لصق اللوجو على الصورة
    canvas = image.copy()
    canvas.paste(logo, (x, y), logo)  # يستخدم alpha channel للشفافية

    # تحويل لـ RGB وحفظ كـ JPEG عالي الجودة
    result = canvas.convert("RGB")
    output = io.BytesIO()
    result.save(output, format="JPEG", quality=95)
    output.seek(0)
    return output.read()


def generate_white_logo_from_black():
    """
    إنشاء نسخة بيضاء من اللوجو الأسود تلقائيًا
    (يُستخدم لو ملف logo_white.png غير موجود)
    """
    if not os.path.exists(LOGO_WHITE_PATH):
        if os.path.exists(LOGO_BLACK_PATH):
            logo = Image.open(LOGO_BLACK_PATH).convert("RGBA")
            r, g, b, a = logo.split()
            
            # عكس الألوان (أسود → أبيض) مع الحفاظ على الشفافية
            from PIL import ImageOps
            rgb = Image.merge("RGB", (r, g, b))
            inverted = ImageOps.invert(rgb)
            ir, ig, ib = inverted.split()
            white_logo = Image.merge("RGBA", (ir, ig, ib, a))
            white_logo.save(LOGO_WHITE_PATH)
            print("✅ تم إنشاء logo_white.png تلقائيًا")
        else:
            print("⚠️ لم يتم العثور على logo_black.png")

