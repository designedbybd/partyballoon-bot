# -*- coding: utf-8 -*-
"""اختبار logo_processor مع لوجو تجريبي"""
from PIL import Image, ImageDraw
import numpy as np
import io, sys, os

sys.stdout.reconfigure(encoding='utf-8')

# انشاء لوجو تجريبي (اسود على شفاف)
logo_black = Image.new('RGBA', (400, 200), (0,0,0,0))
draw = ImageDraw.Draw(logo_black)
draw.rectangle([5,5,395,195], fill=(0,0,0,200))
logo_black.save('logo_black.png')

# نسخة بيضاء
arr = np.array(logo_black)
white = arr.copy()
white[:,:,0] = 255
white[:,:,1] = 255
white[:,:,2] = 255
Image.fromarray(white, 'RGBA').save('logo_white.png')

# صورة اختبار
test_img = Image.new('RGB', (1000, 700), color=(30, 100, 180))
buf = io.BytesIO()
test_img.save(buf, format='JPEG')
test_bytes = buf.getvalue()

# استيراد المعالج
sys.path.insert(0, '.')
from logo_processor import add_logo_to_image

errors = 0
for color in ['black', 'white']:
    for pos in ['top_right', 'top_left', 'bottom_right', 'bottom_left']:
        try:
            result = add_logo_to_image(test_bytes, color, pos)
            size_kb = len(result) // 1024
            print(f"OK: {color} @ {pos} => {size_kb}KB")
        except Exception as e:
            print(f"FAIL: {color} @ {pos} => {e}")
            errors += 1

if errors == 0:
    print("\nAll 8 tests PASSED!")
    # حفظ صورة عينة
    sample = add_logo_to_image(test_bytes, 'black', 'bottom_right')
    with open('sample_output.jpg', 'wb') as f:
        f.write(sample)
    print("Sample saved: sample_output.jpg")
else:
    print(f"\n{errors} test(s) FAILED!")
    sys.exit(1)
