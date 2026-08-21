import subprocess
import os
import shutil


def get_video_duration(file_path):
    """Lấy thời lượng video (giây)"""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ]
    return float(subprocess.check_output(cmd).decode().strip())


def get_best_codec(device="auto"):
    """Phát hiện codec phù hợp: NVENC nếu có GPU, libx264 nếu không"""
    if device == "cpu":
        return "libx264"
    try:
        result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5)
        if "h264_nvenc" in result.stdout:
            return "h264_nvenc"
    except Exception:
        pass
    return "libx264"


def get_codec_config(quality="medium", device="auto"):
    """Chọn preset + bitrate dựa trên chất lượng và thiết bị

    NVENC presets (GPU): p1 (nhanh nhất) -> p7 (chậm nhất, chất lượng cao nhất)
    libx264 presets (CPU): ultrafast (nhanh) -> veryslow (chậm, chất lượng cao)
    """
    codec = get_best_codec(device)

    if codec == "h264_nvenc":
        profiles = {
            "p1":   {"codec": "h264_nvenc", "preset": "p1", "cq": "28", "b:v": "2M", "maxrate": "4M", "bufsize": "4M"},
            "p2":   {"codec": "h264_nvenc", "preset": "p2", "cq": "26", "b:v": "3M", "maxrate": "6M", "bufsize": "6M"},
            "p3":   {"codec": "h264_nvenc", "preset": "p3", "cq": "24", "b:v": "4M", "maxrate": "8M", "bufsize": "8M"},
            "p4":   {"codec": "h264_nvenc", "preset": "p4", "cq": "22", "b:v": "6M", "maxrate": "10M", "bufsize": "12M"},
            "p5":   {"codec": "h264_nvenc", "preset": "p5", "cq": "20", "b:v": "8M", "maxrate": "12M", "bufsize": "16M"},
            "p6":   {"codec": "h264_nvenc", "preset": "p6", "cq": "18", "b:v": "12M", "maxrate": "18M", "bufsize": "24M"},
            "p7":   {"codec": "h264_nvenc", "preset": "p7", "cq": "15", "b:v": "20M", "maxrate": "30M", "bufsize": "40M"},
        }
    else:
        profiles = {
            "p1":   {"codec": "libx264", "preset": "ultrafast", "cq": "28", "b:v": "2M", "maxrate": "4M", "bufsize": "4M"},
            "p2":   {"codec": "libx264", "preset": "superfast",  "cq": "26", "b:v": "3M", "maxrate": "6M", "bufsize": "6M"},
            "p3":   {"codec": "libx264", "preset": "veryfast",   "cq": "24", "b:v": "4M", "maxrate": "8M", "bufsize": "8M"},
            "p4":   {"codec": "libx264", "preset": "faster",     "cq": "23", "b:v": "5M", "maxrate": "9M", "bufsize": "10M"},
            "p5":   {"codec": "libx264", "preset": "medium",     "cq": "22", "b:v": "6M", "maxrate": "10M", "bufsize": "12M"},
            "p6":   {"codec": "libx264", "preset": "slow",       "cq": "18", "b:v": "12M", "maxrate": "18M", "bufsize": "24M"},
            "p7":   {"codec": "libx264", "preset": "veryslow",   "cq": "16", "b:v": "16M", "maxrate": "24M", "bufsize": "32M"},
        }
    return profiles.get(quality, profiles["p4"])


def check_ffmpeg():
    """Kiểm tra FFmpeg có khả dụng không"""
    return shutil.which("ffmpeg") is not None