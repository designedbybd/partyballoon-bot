FROM python:3.11-slim

WORKDIR /app

# تثبيت المكتبات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الملفات
COPY . .

# تشغيل البوت
CMD ["python", "bot.py"]
