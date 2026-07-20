# -*- coding: utf-8 -*-
"""
تحويل اللوجو الأصلي (أسود على خلفية بيضاء) إلى PNG شفاف
يجب وضع الملف الأصلي باسم: logo_source.png في نفس المجلد
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from PIL import Image
import numpy as np
import os

def convert_logo(input_path: str):
    print(f"Processing: {input_path}")
    img = Image.open(input_path).convert("RGBA")
    arr = np.array(img)
    
    # حساب متوسط RGB لكل بيكسل
    brightness = (arr[:,:,0].astype(int) + arr[:,:,1].astype(int) + arr[:,:,2].astype(int)) // 3
    
    # الخلفية البيضاء (> 240) تصبح شفافة، الأسود يبقى معتمًا
    alpha = np.clip(255 - brightness, 0, 255).astype(np.uint8)
    # تجاهل البيكسلات شبه البيضاء
    alpha[brightness > 235] = 0
    
    # لوجو أسود شفاف
    black_arr = np.zeros_like(arr)
    black_arr[:,:,0] = 0
    black_arr[:,:,1] = 0
    black_arr[:,:,2] = 0
    black_arr[:,:,3] = alpha
    
    black_logo = Image.fromarray(black_arr, "RGBA")
    black_logo.save("logo_black.png")
    print("Saved: logo_black.png")
    
    # لوجو أبيض شفاف (عكس الأسود)
    white_arr = np.zeros_like(arr)
    white_arr[:,:,0] = 255
    white_arr[:,:,1] = 255
    white_arr[:,:,2] = 255
    white_arr[:,:,3] = alpha
    
    white_logo = Image.fromarray(white_arr, "RGBA")
    white_logo.save("logo_white.png")
    print("Saved: logo_white.png")
    
    print("\nDone! Both logo_black.png and logo_white.png are ready.")

if __name__ == "__main__":
    # ابحث عن ملف اللوجو الأصلي
    for name in ["logo_source.png", "logo_source.jpg", "logo_original.png", "logo_original.jpg"]:
        if os.path.exists(name):
            convert_logo(name)
            break
    else:
        print("ERROR: Place your logo file as 'logo_source.png' in this folder.")
        sys.exit(1)
