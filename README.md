# 🎈 Party Balloon Logo Bot

بوت تيليجرام يضيف لوجو **Party Balloon** على صورك تلقائيًا!

---

## 📁 محتوى المجلد

```
telegram-logo-bot/
├── bot.py               ✅ الكود الرئيسي
├── logo_processor.py    ✅ معالجة الصور
├── config.py            ✅ الإعدادات
├── logo_black.png       ⬅️ ضعه هنا
├── logo_white.png       ⬅️ ضعه هنا (أو يُنشأ تلقائيًا)
├── .env                 ⬅️ أنشئه وضع التوكن
├── requirements.txt     ✅ المكتبات
├── Dockerfile           ✅ Docker
└── docker-compose.yml   ✅ Docker Compose
```

---

## 🚀 طريقة التشغيل

### الخطوة 1: ضع ملفات اللوجو
انسخ ملفي اللوجو في مجلد المشروع:
- `logo_black.png` — اللوجو بالأسود
- `logo_white.png` — اللوجو بالأبيض

> **ملاحظة:** لو ما عندكش `logo_white.png`، البوت ينشئه تلقائيًا من الأسود!

### الخطوة 2: أنشئ ملف `.env`
```bash
cp .env.example .env
```
ثم افتح `.env` وحط التوكن:
```
BOT_TOKEN=123456789:ABCDEFxxxxxxxxxxxxxxxx
```

### الخطوة 3: شغّل البوت

#### بـ Docker (الأسهل):
```bash
docker-compose up -d
```

#### بدون Docker:
```bash
pip install -r requirements.txt
python bot.py
```

---

## 🤖 طريقة الاستخدام

1. افتح البوت على تيليجرام
2. ابعت صورة
3. اختر **لون اللوجو**: ⚫ أسود أو ⚪ أبيض
4. اختر **موضع اللوجو**: ↗ ↖ ↘ ↙
5. البوت يرجعلك الصورة جاهزة! ✅

---

## ⚙️ تخصيص الإعدادات

في ملف `config.py`:
```python
LOGO_SIZE_RATIO = 0.20  # حجم اللوجو (20% من عرض الصورة)
LOGO_MARGIN = 30        # هامش من الحواف بالبكسل
```

---

## 🔧 الحصول على توكن البوت

1. افتح تيليجرام وتحدث مع [@BotFather](https://t.me/BotFather)
2. اكتب `/newbot`
3. اتبع التعليمات واحصل على التوكن
4. حطه في ملف `.env`
