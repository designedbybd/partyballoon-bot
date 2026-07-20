"""
سكريبت لإنشاء لوجو تجريبي للاختبار
شغّله مرة واحدة بس لو عندك الملفات الأصلية مش محتاجه
"""
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os

def create_test_logos():
    """إنشاء لوجو تجريبي للاختبار"""
    size = (500, 250)
    
    # لوجو أسود على شفاف
    img_black = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img_black)
    draw.rectangle([10, 10, 490, 240], outline=(0, 0, 0, 255), width=3)
    draw.text((50, 80), "PARTY BALLOON", fill=(0, 0, 0, 255))
    draw.text((80, 140), "EVENT PLANNER", fill=(0, 0, 0, 200))
    img_black.save("logo_black.png")
    print("✅ logo_black.png تم إنشاؤه")
    
    # لوجو أبيض على شفاف (عكس الأسود)
    img_white = Image.new("RGBA", size, (0, 0, 0, 0))
    draw2 = ImageDraw.Draw(img_white)
    draw2.rectangle([10, 10, 490, 240], outline=(255, 255, 255, 255), width=3)
    draw2.text((50, 80), "PARTY BALLOON", fill=(255, 255, 255, 255))
    draw2.text((80, 140), "EVENT PLANNER", fill=(255, 255, 255, 200))
    img_white.save("logo_white.png")
    print("✅ logo_white.png تم إنشاؤه")

if __name__ == "__main__":
    create_test_logos()
    print("\n✅ الملفات جاهزة! يمكنك الآن استبدالها بالملفات الأصلية.")
