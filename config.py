import os
from dotenv import load_dotenv

load_dotenv()

# ضع التوكن بتاعك هنا أو في ملف .env
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# مسارات اللوجو
LOGO_BLACK_PATH = "logo_black.png"
LOGO_WHITE_PATH = "logo_white.png"

# حجم اللوجو (نسبة من عرض الصورة)
LOGO_SIZE_RATIO = 0.20  # 20% من عرض الصورة

# هامش من الحواف (بالبكسل)
LOGO_MARGIN = 30
