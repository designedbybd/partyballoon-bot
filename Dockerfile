FROM python:3.11-slim

WORKDIR /app

# تثبيت ffmpeg (لازم لمعالجة الفيديوهات)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# تثبيت المكتبات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الملفات
COPY . .

# تشغيل البوت
CMD ["python", "bot.py"]
