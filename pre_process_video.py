import os
import random
import json
import logging
import subprocess
import argparse
import sys

from utils.ffmpeg import get_codec_config, get_best_codec

logging.basicConfig(level=logging.INFO, format='%(message)s')


def pre_process(task_dir, mode='duck', bgm_file=None, speed=1.0, max_fps=60, quality="medium", device="auto",
                brightness=0, cut_start=0, cut_end=0):
    input_path = os.path.join(task_dir, "original_video.mp4")
    output_path = os.path.join(task_dir, "cleaned_video.mp4")

    if not os.path.exists(input_path):
        logging.error(f"Khong tim thay video goc tai: {input_path}")
        return False

    # Probe video info
    cmd_probe = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", input_path]
    try:
        result = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        video_stream = next(s for s in data['streams'] if s['codec_type'] == 'video')
        w, h = int(video_stream['width']), int(video_stream['height'])
        # Lấy duration
        duration = float(video_stream.get('duration', 0))
        if duration <= 0:
            # fallback format
            fmt_result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", input_path],
                capture_output=True, text=True, check=True
            )
            duration = float(fmt_result.stdout.strip())
    except Exception as e:
        logging.error(f"Loi Probe video: {e}")
        return False

    # Random params for bypass
    v_setpts = round(1.0 / speed, 3)
    r_contrast = round(random.uniform(1.02, 1.08), 2)
    r_sat = round(random.uniform(1.03, 1.10), 2)
    target_fps = min(max_fps, 60)

    # Audio speed filter
    if speed < 0.5:
        a_speed_filter = f"atempo=0.5,atempo={round(speed / 0.5, 3)}"
    elif speed > 2.0:
        a_speed_filter = f"atempo=2.0,atempo={round(speed / 2.0, 3)}"
    else:
        a_speed_filter = f"atempo={speed}"

    # Brightness filter: normalize brightness từ -100..100 sang eq brightness
    # FFmpeg eq brightness range: -1.0 (tối) đến 1.0 (sáng), default 0
    if brightness != 0:
        eq_brightness = round(brightness / 100.0, 3)
        brightness_filter = f":brightness={eq_brightness}"
    else:
        brightness_filter = ""

    # Video filters
    v_filters = (
        f"[0:v]hflip,"
        f"crop=iw*0.99:ih:iw*0.01:0,"
        f"eq=contrast={r_contrast}:saturation={r_sat}:brightness=0.01{brightness_filter},"
        f"fps={target_fps},setpts={v_setpts}*PTS[vout]"
    )

    # Cut start/end using -ss and -to
    inputs = ["-i", input_path]
    cut_params = []
    if cut_start > 0:
        cut_params.extend(["-ss", str(cut_start)])
    if cut_end > 0:
        # Tính toán thời lượng cần giữ
        if duration > cut_end:
            cut_to = duration - cut_end
            cut_params.extend(["-to", str(cut_to)])
        else:
            logging.warning(f"cut_end ({cut_end}s) > video duration ({duration}s), bỏ qua cắt cuối")

    if bgm_file:
        bgm_path = os.path.abspath(os.path.join("bgm", bgm_file))
        if os.path.exists(bgm_path):
            inputs = ["-i", input_path, "-stream_loop", "-1", "-i", bgm_path]
            if mode == 'mute':
                a_filters = f"[1:a]{a_speed_filter},volume=0.5,aresample=48000[aout]"
            else:
                a_filters = (
                    f"[0:a]volume=0.4,{a_speed_filter}[a_orig];"
                    f"[1:a]{a_speed_filter},volume=0.2[a_bgm];"
                    f"[a_orig][a_bgm]amix=inputs=2:duration=first,aresample=48000[aout]"
                )
        else:
            logging.warning(f"Khong tim thay BGM: {bgm_path}")
            a_filters = f"[0:a]{a_speed_filter},aresample=48000[aout]"
    else:
        a_filters = f"[0:a]{a_speed_filter},aresample=48000[aout]" if mode != 'mute' else f"[0:a]volume=0,aresample=48000[aout]"

    # Get codec config from central config
    codec_cfg = get_codec_config(quality, device)

    ffmpeg_cmd = ["ffmpeg", "-y"] + cut_params + inputs + [
        "-filter_complex", f"{v_filters};{a_filters}",
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", codec_cfg["codec"],
        "-preset", codec_cfg["preset"],
        "-rc", "vbr",
        "-cq", codec_cfg["cq"],
        "-b:v", codec_cfg["b:v"],
        "-maxrate", codec_cfg["maxrate"],
        "-bufsize", codec_cfg.get("bufsize", "16M"),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-map_metadata", "-1",
        output_path
    ]

    try:
        logging.info(f"Dang tien xu ly Video: {os.path.basename(task_dir)} ({codec_cfg['codec']})")
        if cut_start > 0 or cut_end > 0:
            logging.info(f"Cat video: dau {cut_start}s, cuoi {cut_end}s")
        if brightness != 0:
            logging.info(f"Do sang: {brightness}")
        subprocess.run(ffmpeg_cmd, check=True)

        # Binary padding for MD5 bypass
        with open(output_path, "ab") as f:
            f.write(os.urandom(random.randint(100, 500)))

        logging.info(f"Da tao video sach tai: {output_path}")
        return True
    except Exception as e:
        logging.error(f"Loi tien xu ly: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task_dir", required=True)
    parser.add_argument("--mode", choices=['mute', 'duck'], default='duck')
    parser.add_argument("--bgm", default=None)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--quality", default="medium", help="fast/medium/high")
    parser.add_argument("--device", default="auto", help="auto/cuda/cpu")
    parser.add_argument("--brightness", type=int, default=0, help="Độ sáng (-100..100)")
    parser.add_argument("--cut_start", type=int, default=0, help="Cắt đầu (giây)")
    parser.add_argument("--cut_end", type=int, default=0, help="Cắt cuối (giây)")
    args = parser.parse_args()

    success = pre_process(args.task_dir, args.mode, args.bgm, args.speed, args.fps, args.quality, args.device,
                          args.brightness, args.cut_start, args.cut_end)
    if not success:
        sys.exit(1)