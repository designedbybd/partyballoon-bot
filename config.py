import os
from dotenv import load_dotenv

load_dotenv()

# ضع التوكن بتاعك هنا أو في ملف .env
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# مسارات اللوجو
LOGO_BLACK_PATH = "logo_black.PNG"
LOGO_WHITE_PATH = "logo_white.PNG"

# حجم اللوجو (نسبة من عرض الصورة)
LOGO_SIZE_RATIO = 0.26  # 26% من عرض الصورة (تم تكبيرها شوية)

# هامش من الحواف (بالبكسل)
LOGO_MARGIN = 30

# معرف القناة لحفظ الصور
CHANNEL_ID = "-1004368547666"

