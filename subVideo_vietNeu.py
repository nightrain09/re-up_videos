import os

# Ẩn cảnh báo gRPC ALTS từ Google Cloud
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

import subprocess
import re
import argparse
import shutil
import asyncio
import hashlib
import torch
from datetime import datetime
from pydub import AudioSegment
from vieneu import Vieneu

from utils.task_progress import (
    empty_progress,
    get_stage,
    load_progress_file,
    save_progress_file,
)

# =========================================================
# --- CẤU HÌNH CỐ ĐỊNH (CHỈ GIỮ BIẾN LIÊN QUAN VIENEU) ---
# =========================================================
# File mẫu 10s để clone giọng VieNeu
REFERENCE_VOICE = "mau.mp3"

# Cấu hình Audio
SAMPLE_RATE = 44100
DVOICE_RATE = 1.4  # Tốc độ mặc định áp dụng cho VieNeu

# Cấu hình hệ thống
MAX_CONCURRENT_TTS = 1
# =========================================================

# Khởi tạo Engine VieNeu
print("--- Đang khởi tạo hệ thống VieNeu TTS ---")
tts_engine = Vieneu()
ref_voice_data = None
if os.path.exists(REFERENCE_VOICE):
    ref_voice_data = tts_engine.encode_reference(REFERENCE_VOICE)


def speed_change_smooth(seg, vr_rate):
    if vr_rate == 1.0:
        return seg

    tmp_in = f"tmp_in_{datetime.now().strftime('%H%M%S%f')}.wav"
    tmp_out = f"tmp_out_{datetime.now().strftime('%H%M%S%f')}.wav"

    try:
        seg.export(tmp_in, format="wav")
        cmd = [
            "ffmpeg", "-y", "-i", tmp_in,
            "-filter:a", f"atempo={vr_rate}",
            "-vn", tmp_out
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 0:
            new_seg = AudioSegment.from_file(tmp_out)
            return new_seg
        else:
            return seg
    except Exception as e:
        print(f"(!) Speedup Exception: {e}")
        return seg
    finally:
        for f in [tmp_in, tmp_out]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass


def get_video_duration(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
           file_path]
    return float(subprocess.check_output(cmd))


def parse_txt(txt_path):
    if not os.path.exists(txt_path): return []
    subs = []
    pattern = re.compile(r'\[(\d{1,2}):(\d{2}):(\d{2}),(\d{3})\]\s*(.*)')
    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                h, m, s, ms_part = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
                ms = (h * 3600 + m * 60 + s) * 1000 + ms_part
                subs.append({'start_ms': ms, 'text': match.group(5)})
    return subs


def ms_to_ass_time(ms):
    total_seconds = max(0, ms) / 1000.0
    h, m, s = int(total_seconds // 3600), int((total_seconds % 3600) // 60), int(total_seconds % 60)
    cs = int((ms % 1000) // 10)
    return f"{h:02d}:{m:02d}:{s:02d}.{cs:02d}"


def _tts_part_path(path):
    base, ext = os.path.splitext(path)
    return f"{base}.tmp{ext}"


async def generate_tts_safe(text, output_path, semaphore):
    async with semaphore:
        while True:
            tmp_path = _tts_part_path(output_path)
            try:
                loop = asyncio.get_event_loop()
                audio = await loop.run_in_executor(None, lambda: tts_engine.infer(text=text, voice=ref_voice_data))
                await loop.run_in_executor(None, lambda: tts_engine.save(audio, tmp_path))
                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    os.replace(tmp_path, output_path)
                    return True
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                await asyncio.sleep(2)
            except:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
                await asyncio.sleep(2)


def process_rvc_sub(task_dir, blur_sub, final_output_path, sub_file, speed, bgm,
                    blur_start_percent=80, blur_end_percent=95, blur_intensity=10,
                    sub_background=True, has_subtitle=True, progress_file=None):
    task_dir = os.path.abspath(task_dir)
    video_in = os.path.join(task_dir, "original_video.mp4")
    txt_in = sub_file if sub_file else os.path.join(task_dir, "translated.txt")
    video_tmp = os.path.join(task_dir, "rvc_internal_result.mp4")

    subs = parse_txt(txt_in)
    if not subs and has_subtitle: return False

    raw_p = os.path.join(task_dir, "raw_tmp_audio")
    os.makedirs(raw_p, exist_ok=True)

    progress_file = progress_file or os.path.join(task_dir, "progress.json")
    progress = load_progress_file(progress_file) or empty_progress()
    render = get_stage(progress, "render")
    subs_hash = hashlib.sha256((
        "\n".join(f"{s['start_ms']}|{s['text']}" for s in subs)
        + f"|VIENEU|{DVOICE_RATE}|{speed}"
    ).encode("utf-8")).hexdigest()
    if render.get("subs_hash") and render.get("subs_hash") != subs_hash:
        print("[RESUME] Subtitle/voice thay doi -> tao lai TTS.")
        shutil.rmtree(raw_p, ignore_errors=True)
        os.makedirs(raw_p, exist_ok=True)
        render.clear()
    render["subs_hash"] = subs_hash
    render["done"] = False
    save_progress_file(progress_file, progress)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TTS)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tts_done = set(render.get("tts_done") or [])
    batch_size = 15
    for start in range(0, len(subs), batch_size):
        end = min(start + batch_size, len(subs))
        tasks = []
        for i in range(start, end):
            path = os.path.join(raw_p, f"{i}.wav")
            if os.path.exists(path) and os.path.getsize(path) > 100:
                tts_done.add(i)
                continue
            tasks.append(generate_tts_safe(subs[i]['text'], path, semaphore))
        if tasks:
            loop.run_until_complete(asyncio.gather(*tasks))
        for i in range(start, end):
            path = os.path.join(raw_p, f"{i}.wav")
            if os.path.exists(path) and os.path.getsize(path) > 100:
                tts_done.add(i)
        render["tts_done"] = sorted(tts_done)
        render["tts_total"] = len(subs)
        save_progress_file(progress_file, progress)

    video_dur = get_video_duration(video_in)
    combined_voice = AudioSegment.silent(duration=int(video_dur * 1000), frame_rate=SAMPLE_RATE)

    events = []
    for i, sub in enumerate(subs):
        start_sub_ms = int(sub['start_ms'] / speed)
        f_path = os.path.join(raw_p, f"{i}.wav")
        duration_ms = 2000

        if os.path.exists(f_path):
            try:
                audio_seg = AudioSegment.from_file(f_path)

                # Logic tăng tốc audio kết hợp DVOICE_RATE và speed đầu vào
                total_speed = DVOICE_RATE * speed
                if total_speed != 1.0:
                    audio_seg = speed_change_smooth(audio_seg, total_speed)

                duration_ms = len(audio_seg)
                combined_voice = combined_voice.overlay(audio_seg, position=start_sub_ms)
            except:
                pass

        if has_subtitle:
            end_sub_ms = start_sub_ms + duration_ms + 300
            if i + 1 < len(subs):
                next_start = int(subs[i + 1]['start_ms'] / speed)
                if end_sub_ms > next_start: end_sub_ms = next_start - 10
            events.append(
                f"Dialogue: 0,{ms_to_ass_time(start_sub_ms)},{ms_to_ass_time(end_sub_ms)},Default,,0,0,0,,{sub['text']}")

    combined_audio_file = os.path.join(task_dir, "combined_voice_final.wav")
    combined_voice.export(combined_audio_file, format="wav")

    from utils.video_profiles import get_blur_filter_params
    blur_params = get_blur_filter_params(blur_start_percent, blur_end_percent, blur_intensity)

    if has_subtitle:
        temp_ass = os.path.join(task_dir, "final_sub_generated.ass")
        # Luôn đặt phụ đề trong vùng blur, bất kể flag --blur có bật hay không
        from utils.video_profiles import get_subtitle_alignment_from_blur, get_subtitle_margin_from_blur
        from utils.subtitle import generate_ass
        alignment = get_subtitle_alignment_from_blur(blur_start_percent, blur_end_percent)
        margin_v = get_subtitle_margin_from_blur(blur_start_percent, blur_end_percent, alignment, font_size=28)
        border_style = 3 if sub_background else 1
        outline_val = 2 if sub_background else 3
        shadow_val = 0 if sub_background else 1
        generate_ass(events, temp_ass, font_size=28, alignment=alignment, margin_v=margin_v,
                     font_name="Arial", font_color="#FFFF00", outline_color="#000000", back_color="#80000000", bold=True,
                     border_style=border_style, outline=outline_val, shadow=shadow_val)

        # Tính blur params động dựa trên % range
        v_filter = f"ass='{temp_ass}'"
        if blur_sub:
            blur_crop = blur_params["crop"]
            blur_overlay = blur_params["overlay"]
            v_filter = f"split[m][s];[s]crop={blur_crop},{blur_params['blur']}[sb];[m][sb]overlay={blur_overlay},{v_filter}[vout]"
        else:
            v_filter = f"{v_filter}[vout]"
    else:
        temp_ass = None
        if blur_sub:
            blur_crop = blur_params["crop"]
            blur_overlay = blur_params["overlay"]
            v_filter = f"split[m][s];[s]crop={blur_crop},{blur_params['blur']}[sb];[m][sb]overlay={blur_overlay}[vout]"
        else:
            v_filter = "null[vout]"

    # Logic Audio Mix y hệt subVideo_rvc
    if bgm and os.path.exists(bgm):
        a_filter = f"[0:a]volume=0.15[orig];[1:a]volume=1.5[v_tts];[2:a]volume=0.4,loop=loop=-1:size=2e+09[bgm];[orig][v_tts][bgm]amix=inputs=3:duration=first[aout]"
        audio_inputs = ["-i", combined_audio_file, "-i", bgm]
    else:
        a_filter = f"[0:a]volume=0.15[orig];[1:a]volume=1.5[v_tts];[orig][v_tts]amix=inputs=2:duration=first[aout]"
        audio_inputs = ["-i", combined_audio_file]

    filter_script_path = os.path.join(task_dir, "ffmpeg_filter_script.txt")
    with open(filter_script_path, "w", encoding='utf-8') as f:
        f.write(f"[0:v]{v_filter};{a_filter}")

    cmd = [
        "ffmpeg", "-y", "-i", video_in
    ] + audio_inputs + [
        "-filter_complex_script", filter_script_path, "-map", "[vout]", "-map", "[aout]",
        "-c:v", "h264_nvenc", "-preset", "p1", "-c:a", "aac", "-b:a", "320k", video_tmp
    ]
    subprocess.run(cmd, check=True)

    cleanup_list = [raw_p, filter_script_path, combined_audio_file]
    if temp_ass:
        cleanup_list.append(temp_ass)
    for p in cleanup_list:
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.exists(p):
            os.remove(p)

    if os.path.exists(video_tmp):
        os.replace(video_tmp, final_output_path)
        render["done"] = True
        save_progress_file(progress_file, progress)
        return True
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task_dir", required=True)
    parser.add_argument("--blur", action="store_true")
    parser.add_argument("--output", required=True)
    parser.add_argument("--sub", default=None)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--bgm", default=None)
    parser.add_argument("--tts_engine", default="VIENEU")
    parser.add_argument("--sub_background", default="True", help="Bật/tắt nền phụ đề (True/False)")
    parser.add_argument("--has_subtitle", default="True", help="Co chay TTS+chen phu de hay khong (True/False)")
    parser.add_argument("--progress", default=None, help="File progress.json cua task")
    # MainController truyền chung nhiều tham số cho mọi render script; VieNeu
    # không dùng hết, nên bỏ qua các arg lạ thay vì lỗi argparse.
    args, _ = parser.parse_known_args()
    sub_bg = args.sub_background.lower() in ("true", "1", "yes")
    has_subtitle = args.has_subtitle.lower() in ("true", "1", "yes")
    process_rvc_sub(args.task_dir, args.blur, args.output, args.sub, args.speed, args.bgm,
                    sub_background=sub_bg, has_subtitle=has_subtitle,
                    progress_file=args.progress)
