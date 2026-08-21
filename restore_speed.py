import subprocess
import argparse
import sys
import os
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(message)s')


def restore_video_speed(input_path, output_path, original_speed, target_fps):
    if not os.path.exists(input_path):
        logging.error(f"Lỗi: Không tìm thấy file đầu vào tại {input_path}")
        return False

    # Tính toán tốc độ khôi phục (nghịch đảo của speed ban đầu)
    # Ví dụ: Ban đầu speed=0.5 (chậm), thì recovery_speed = 2.0 (tăng tốc để về gốc)
    recovery_speed = round(1.0 / original_speed, 3)
    v_setpts = round(1.0 / recovery_speed, 3)

    # Xử lý bộ lọc âm thanh atempo (Giới hạn của FFmpeg là 0.5 đến 2.0 mỗi bộ lọc)
    # Nếu recovery_speed vượt quá ngưỡng này, phải dùng chuỗi filter (chaining)
    if recovery_speed < 0.5:
        a_filter = f"atempo=0.5,atempo={round(recovery_speed / 0.5, 3)},aresample=48000"
    elif recovery_speed > 2.0:
        a_filter = f"atempo=2.0,atempo={round(recovery_speed / 2.0, 3)},aresample=48000"
    else:
        a_filter = f"atempo={recovery_speed},aresample=48000"

    # Lệnh FFmpeg để đưa video/audio về thời lượng gốc và áp FPS mục tiêu
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-filter_complex", f"[0:v]fps={target_fps},setpts={v_setpts}*PTS[vout];[0:a]{a_filter}[aout]",
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]

    try:
        logging.info(f"--- Đang khôi phục tốc độ: {recovery_speed}x (PTS: {v_setpts}) ---")
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Lỗi FFmpeg khi khôi phục tốc độ: {e}")
        return False
    except Exception as e:
        logging.error(f"Lỗi không xác định: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Khôi phục tốc độ video về nguyên bản")
    parser.add_argument("--task_dir", required=True)
    parser.add_argument("--speed", type=float, required=True)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--input_file", required=True)
    parser.add_argument("--output_file", required=True)

    args = parser.parse_args()

    success = restore_video_speed(
        args.input_file,
        args.output_file,
        args.speed,
        args.fps
    )

    if not success:
        sys.exit(1)