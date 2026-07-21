"""
معالجة الفيديوهات وإضافة اللوجو
Video Processor - Party Balloon Bot
(بيستخدم ffmpeg اللي لازم يكون متثبت على السيرفر)
"""
import json
import os
import subprocess
import tempfile

from logo_processor import prepare_logo, get_logo_position
from config import LOGO_BLACK_PATH, LOGO_WHITE_PATH


class VideoProcessingError(Exception):
    """خطأ أثناء معالجة الفيديو (ffmpeg مش متثبت، أو الفيديو تالف، ...)"""
    pass


def _ffmpeg_available() -> bool:
    from shutil import which
    return which("ffmpeg") is not None and which("ffprobe") is not None


def _probe_video_size(video_path: str) -> tuple:
    """يرجع (width, height) للفيديو باستخدام ffprobe"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        video_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise VideoProcessingError(f"تعذّر قراءة بيانات الفيديو: {proc.stderr.strip()}")

    data = json.loads(proc.stdout)
    streams = data.get("streams", [])
    if not streams:
        raise VideoProcessingError("الفيديو مش شكله سليم (مفيش video stream).")

    width = int(streams[0]["width"])
    height = int(streams[0]["height"])
    return width, height


def add_logo_to_video(video_bytes: bytes, color: str, position: str, size_ratio: float = None) -> bytes:
    """
    إضافة اللوجو على فيديو باستخدام ffmpeg

    Args:
        video_bytes: بيانات الفيديو
        color: "black" أو "white"
        position: "top_right" / "top_left" / "bottom_right" / "bottom_left"
                  / "top_center" / "bottom_center"
        size_ratio: نسبة حجم اللوجو من عرض الفيديو (اختياري)

    Returns:
        بيانات الفيديو بعد إضافة اللوجو (MP4)
    """
    if not _ffmpeg_available():
        raise VideoProcessingError(
            "ffmpeg مش متثبت على السيرفر. لازم تتثبت ffmpeg الأول عشان معالجة الفيديوهات تشتغل."
        )

    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = os.path.join(tmp_dir, "input.mp4")
        logo_path = os.path.join(tmp_dir, "logo.png")
        output_path = os.path.join(tmp_dir, "output.mp4")

        with open(input_path, "wb") as f:
            f.write(video_bytes)

        # حجم الفيديو الحقيقي
        video_w, video_h = _probe_video_size(input_path)

        # تحضير اللوجو بنفس نسبة الحجم المستخدمة مع الصور
        source_logo_path = LOGO_BLACK_PATH if color == "black" else LOGO_WHITE_PATH
        logo_img = prepare_logo(source_logo_path, video_w, size_ratio)
        logo_img.save(logo_path, format="PNG")
        logo_w, logo_h = logo_img.size

        # حساب موضع اللوجو (نفس منطق الصور بالظبط)
        x, y = get_logo_position(position, video_w, video_h, logo_w, logo_h)

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-loop", "1", "-i", logo_path,
            "-filter_complex", f"[0:v][1:v]overlay={x}:{y}:shortest=1[outv]",
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise VideoProcessingError(f"فشلت معالجة الفيديو: {proc.stderr[-800:]}")

        with open(output_path, "rb") as f:
            return f.read()
