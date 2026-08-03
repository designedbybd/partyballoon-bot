import os
from dotenv import load_dotenv

load_dotenv()

# ضع التوكن بتاعك هنا أو في ملف .env
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# مسارات اللوجو
LOGO_BLACK_PATH = "logo_black.PNG"
LOGO_WHITE_PATH = "logo_white.PNG"

# مقاسات اللوجو المتاحة للمستخدم (نسبة من عرض الصورة/الفيديو)
LOGO_SIZE_OPTIONS = {
    "small":  0.16,
    "medium": 0.22,
    "large":  0.30,
    "xlarge": 0.38,
}

# حجم اللوجو الافتراضي (نسبة من عرض الصورة) — بيتستخدم لو المقاس مش متحدد
LOGO_SIZE_RATIO = LOGO_SIZE_OPTIONS["medium"]

# هامش من الحواف (بالبكسل)
LOGO_MARGIN = 30

# معرف القناة لحفظ الصور
CHANNEL_ID = "-1004368547666"
