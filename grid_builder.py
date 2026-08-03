"""
منشئ الجريد (Grid Collage)
يجمع مجموعة صور في تصميم واحد ملازق بعضه، بمقاس الستوري (1080x1920)
مع اللوجو في منتصف الصورة بالظبط
"""
import io
import math
from PIL import Image, ImageDraw

from logo_processor import prepare_logo
from config import LOGO_BLACK_PATH, LOGO_WHITE_PATH

STORY_SIZE = (1080, 1920)


def _fit_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """يكبّر/يصغّر الصورة وتقصها عشان تملى المساحة المطلوبة بالظبط من غير تفريغ"""
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = max(1, int(src_w * scale) + 1), max(1, int(src_h * scale) + 1)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _compute_grid(n: int, canvas_w: int, canvas_h: int):
    """يحسب عدد الأعمدة والصفوف المناسب لأي عدد صور N"""
    aspect = canvas_h / canvas_w  # نسبة الكانفاس (طولي)
    cols = max(1, round(math.sqrt(n / aspect)))
    rows = math.ceil(n / cols)
    # لو الصف الأخير هيبقى فاضي أوي، زوّد الأعمدة لتوزيع أحسن
    while cols < n and (rows * cols - n) >= cols:
        cols += 1
        rows = math.ceil(n / cols)
    return cols, rows


def create_grid_story(
    photos_bytes: list,
    logo_color: str = "white",
    size_ratio: float = 0.24,
) -> bytes:
    """
    يجمع مجموعة صور في جريد واحد بمقاس الستوري (1080x1920) مع اللوجو في المنتصف

    Args:
        photos_bytes: لستة بيانات الصور (bytes)
        logo_color: "black" أو "white"
        size_ratio: نسبة حجم اللوجو من عرض الكانفاس

    Returns:
        بيانات الصورة النهائية (JPEG)
    """
    n = len(photos_bytes)
    if n < 1:
        raise ValueError("لازم صورة واحدة على الأقل")

    canvas_w, canvas_h = STORY_SIZE
    canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))

    cols, rows = _compute_grid(n, canvas_w, canvas_h)

    idx = 0
    for r in range(rows):
        remaining = n - idx
        if remaining <= 0:
            break
        images_in_row = min(cols, remaining)
        y = round(r * canvas_h / rows)
        y2 = round((r + 1) * canvas_h / rows)
        for c in range(images_in_row):
            x = round(c * canvas_w / images_in_row)
            x2 = round((c + 1) * canvas_w / images_in_row)
            img = Image.open(io.BytesIO(photos_bytes[idx])).convert("RGB")
            fitted = _fit_cover(img, x2 - x, y2 - y)
            canvas.paste(fitted, (x, y))
            idx += 1

    # ─── اللوجو في المنتصف بالظبط، مع خلفية شفافة عشان يبان مهما كان لون الصور تحته ───
    logo_path = LOGO_BLACK_PATH if logo_color == "black" else LOGO_WHITE_PATH
    logo_img = prepare_logo(logo_path, canvas_w, size_ratio)
    logo_w, logo_h = logo_img.size

    pad = int(logo_w * 0.18)
    backdrop_w = logo_w + pad * 2
    backdrop_h = logo_h + pad * 2
    # خلفية غامقة لو اللوجو أبيض، وخلفية فاتحة لو اللوجو أسود (عشان يفضل واضح فوق أي لون)
    backdrop_color = (0, 0, 0, 130) if logo_color == "white" else (255, 255, 255, 150)

    backdrop = Image.new("RGBA", (backdrop_w, backdrop_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(backdrop)
    draw.rounded_rectangle(
        [0, 0, backdrop_w, backdrop_h],
        radius=int(backdrop_h * 0.22),
        fill=backdrop_color,
    )

    bx = (canvas_w - backdrop_w) // 2
    by = (canvas_h - backdrop_h) // 2

    canvas_rgba = canvas.convert("RGBA")
    canvas_rgba.paste(backdrop, (bx, by), backdrop)

    logo_x = (canvas_w - logo_w) // 2
    logo_y = (canvas_h - logo_h) // 2
    canvas_rgba.paste(logo_img, (logo_x, logo_y), logo_img)

    canvas = canvas_rgba.convert("RGB")

    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=92)
    return buf.getvalue()
