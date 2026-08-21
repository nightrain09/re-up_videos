import os
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

import subprocess
import re
import argparse
import shutil
import asyncio
import aiohttp
import tempfile
from datetime import datetime
from pydub import AudioSegment
from pydub.effects import normalize
from google.cloud import texttospeech
import edge_tts
from gtts import gTTS

from utils.audio import speed_change, trim_silence
from utils.subtitle import parse_txt, ms_to_ass_time, generate_ass
from utils.ffmpeg import get_video_duration, get_codec_config, get_best_codec
from utils.tts_cache import get_cache
from utils.video_profiles import detect_aspect_ratio, get_blur_filter_params

# Default config
KEY_PATH = "service-account.json"
SELECT_TYPE = "EDGE"
FINAL_VOICE_ID = "vi-VN-Chirp3-HD-Aoede"
NEUTRAL_VOICE_ID = "vi-VN-Wavenet-C"
EDGE_VOICE = "vi-VN-HoaiMyNeural"
LANGUAGE_CODE = "vi-VN"
PITCH = 8.0
AUDIO_ENCODING = texttospeech.AudioEncoding.LINEAR16
SAMPLE_RATE = 44100
DVOICE_RATE = 1.1
VOICE_RATE = 1.5
GTTSVOICE_RATE = 1.5
EDGE_RATE = "+25%"
MAX_CONCURRENT_TTS = 2
CHUNK_SIZE = 15
MAX_RETRIES = 5  # Gioi han retry de tranh loop vo han

# TikTokTTS config
TIKTOKTTS_HOST = "http://localhost:8080"
TIKTOKTTS_VOICE = "cutefemale"
TIKTOKTTS_PITCH = 0
TIKTOKTTS_SPEED = 10

client = None


def init_google_client():
    global client
    if SELECT_TYPE in ["CHIRP", "NEUTRAL"]:
        try:
            if os.path.exists(KEY_PATH):
                client = texttospeech.TextToSpeechClient.from_service_account_json(KEY_PATH)
            else:
                root_key = os.path.join(os.path.dirname(os.path.abspath(__file__)), KEY_PATH)
                if os.path.exists(root_key):
                    client = texttospeech.TextToSpeechClient.from_service_account_json(root_key)
                else:
                    raise Exception(f"Khong tim thay file token {KEY_PATH}.")
        except Exception as e:
            print(f"Loi Google Cloud: {e}")
            raise e


async def generate_tts_safe(text, output_path, semaphore):
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                success = False
                if SELECT_TYPE in ["CHIRP", "NEUTRAL"]:
                    if not client:
                        print("LOI: Google Cloud Client chua duoc khoi tao.")
                        exit(1)
                    synthesis_input = texttospeech.SynthesisInput(text=text)
                    v_id = FINAL_VOICE_ID if SELECT_TYPE == "CHIRP" else NEUTRAL_VOICE_ID
                    voice = texttospeech.VoiceSelectionParams(language_code=LANGUAGE_CODE, name=v_id)
                    audio_config = texttospeech.AudioConfig(
                        audio_encoding=AUDIO_ENCODING, sample_rate_hertz=SAMPLE_RATE,
                        speaking_rate=DVOICE_RATE, pitch=PITCH
                    )
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None, lambda: client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
                    )
                    if response.audio_content:
                        with open(output_path, "wb") as out:
                            out.write(response.audio_content)
                        success = True

                elif SELECT_TYPE == "EDGE":
                    communicate = edge_tts.Communicate(text=text, voice=EDGE_VOICE, rate=EDGE_RATE, volume="+0%")
                    with open(output_path, "wb") as f:
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                f.write(chunk["data"])
                    success = True

                elif SELECT_TYPE == "GTTS":
                    tts = gTTS(text=text, lang='vi', slow=False)
                    tts.save(output_path)
                    success = True

                elif SELECT_TYPE == "TIKTOKTTS":
                    async with aiohttp.ClientSession() as session:
                        url = f"{TIKTOKTTS_HOST}/v2/synthesize"
                        body = {
                            "text": text, "speaker": TIKTOKTTS_VOICE,
                            "speed": TIKTOKTTS_SPEED, "volume": 1000, "method": "buffer"
                        }
                        async with session.post(url, json=body, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                            if resp.status == 200:
                                data = await resp.read()
                                if data:
                                    with open(output_path, "wb") as f:
                                        f.write(data)
                                    success = True

                if success:
                    return True

                # Retry with backoff
                await asyncio.sleep(min(2 * (attempt + 1), 10))

            except Exception as e:
                if "429" in str(e):
                    await asyncio.sleep(10)
                else:
                    await asyncio.sleep(2)

        print(f"[TTS] Da thu {MAX_RETRIES} lan van that bai cho: {text[:30]}...")
        return False


async def run_tts_batch(subs, raw_p):
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TTS)
    ext = ".wav" if SELECT_TYPE in ["CHIRP", "NEUTRAL"] and AUDIO_ENCODING == texttospeech.AudioEncoding.LINEAR16 else ".mp3"
    for i in range(0, len(subs), CHUNK_SIZE):
        chunk = subs[i: i + CHUNK_SIZE]
        tasks = [generate_tts_safe(sub['text'], os.path.join(raw_p, f"{i + j}{ext}"), semaphore) for j, sub in enumerate(chunk)]
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.5)


def detect_video_aspect(video_path):
    """Doc kich thuoc video tu ffprobe de phat hien ty le"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-of", "csv=p=0", video_path],
            capture_output=True, text=True, check=True
        )
        parts = result.stdout.strip().split(",")
        if len(parts) == 2:
            w, h = int(parts[0]), int(parts[1])
            return detect_aspect_ratio(w, h)
    except:
        pass
    return "16:9"  # default


def process_video_only_tts(task_dir, blur_sub, final_output_path, sub_file, speed,
                           quality="medium", device="auto",
                           subtitle_position="duoi_giua", font_size=32, margin_v=40,
                           blur_start_percent=80, blur_end_percent=95, blur_intensity=10,
                           aspect_ratio="auto", font_name="Arial",
                           font_color="#FFFF00", outline_color="#000000", back_color="#80000000", bold=True,
                           sub_background=True, has_subtitle=True):
    task_dir = os.path.abspath(task_dir)
    video_in = os.path.join(task_dir, "original_video.mp4")
    txt_in = sub_file if sub_file else os.path.join(task_dir, "translated.txt")
    
    # Phát hiện tỷ lệ video: auto hoặc chọn tay
    if aspect_ratio == "auto":
        aspect_ratio = detect_video_aspect(video_in)
    print(f"[VIDEO] Tỷ lệ: {aspect_ratio}, Blur: {blur_start_percent}%->{blur_end_percent}% (độ: {blur_intensity}), Font: {font_name}, Màu: {font_color}")
    blur_params = get_blur_filter_params(blur_start_percent, blur_end_percent, blur_intensity)

    subs = parse_txt(txt_in)
    if not subs and has_subtitle:
        print("[!] Khong tim thay subtitle.")
        return False

    raw_p = os.path.join(task_dir, "raw_tmp_audio")
    os.makedirs(raw_p, exist_ok=True)

    # Use TTS cache
    cache = get_cache()
    asyncio.run(run_tts_batch(subs, raw_p))

    ext = ".wav" if SELECT_TYPE in ["CHIRP", "NEUTRAL"] and AUDIO_ENCODING == texttospeech.AudioEncoding.LINEAR16 else ".mp3"

    video_dur = get_video_duration(video_in)
    combined_voice = AudioSegment.silent(duration=int(video_dur * 1000), frame_rate=SAMPLE_RATE)

    events = []
    is_speed_one = float(speed) == 1.0

    for i, sub in enumerate(subs):
        start_sub_ms = int(sub['start_ms']) if is_speed_one else int(sub['start_ms'] / speed)
        f_path = os.path.join(raw_p, f"{i}{ext}")
        duration_ms = 2000

        if os.path.exists(f_path) and os.path.getsize(f_path) > 100:
            try:
                seg = AudioSegment.from_file(f_path)
                seg = normalize(seg)
                seg = trim_silence(seg)
                vr = GTTSVOICE_RATE if SELECT_TYPE == "GTTS" else VOICE_RATE
                seg = speed_change(seg, vr)
                duration_ms = len(seg)
                combined_voice = combined_voice.overlay(seg, position=start_sub_ms)
            except Exception as e:
                print(f"[!] Loi audio cau {i}: {e}")

        if has_subtitle:
            end_sub_ms = start_sub_ms + duration_ms + 300
            if i + 1 < len(subs):
                next_start = int(subs[i + 1]['start_ms']) if is_speed_one else int(subs[i + 1]['start_ms'] / speed)
                if end_sub_ms > next_start:
                    end_sub_ms = next_start - 10
            events.append(f"Dialogue: 0,{ms_to_ass_time(start_sub_ms)},{ms_to_ass_time(end_sub_ms)},Default,,0,0,0,,{sub['text']}")

    combined_audio_file = os.path.join(task_dir, "combined_voice_final.wav")
    combined_voice.export(combined_audio_file, format="wav")

    # Xay dung filter_complex
    if has_subtitle:
        temp_ass = os.path.join(task_dir, "final_sub_generated.ass")
        # Luôn đặt phụ đề trong vùng blur, bất kể flag --blur có bật hay không
        from utils.video_profiles import get_subtitle_alignment_from_blur, get_subtitle_margin_from_blur
        alignment = get_subtitle_alignment_from_blur(blur_start_percent, blur_end_percent)
        margin_v = get_subtitle_margin_from_blur(blur_start_percent, blur_end_percent, alignment, font_size)
        border_style = 3 if sub_background else 1
        outline_val = 2 if sub_background else 3
        shadow_val = 0 if sub_background else 1
        generate_ass(events, temp_ass, font_size=font_size, alignment=alignment, margin_v=margin_v,
                     font_name=font_name, font_color=font_color, outline_color=outline_color, back_color=back_color, bold=bold,
                     border_style=border_style, outline=outline_val, shadow=shadow_val)

        # [WINDOWS FIX] Thay backslash bằng forward slash, escape colon để FFmpeg không parse sai
        # FFmpeg dùng : làm separator giữa các option filter, nên C: bị hiểu là option name
        ass_path_filter = temp_ass.replace(chr(92), '/').replace(':', '\\:')
        filter_script_path = os.path.join(task_dir, "ffmpeg_filter_script.txt")

        # [WINDOWS FIX] Dùng cú pháp ass='path' sau khi đã escape colon
        v_filter = f"ass='{ass_path_filter}'"
        if blur_sub:
            blur_crop = blur_params["crop"]
            blur_overlay = blur_params["overlay"]
            v_filter = f"split[m][s];[s]crop={blur_crop},{blur_params['blur']}[sb];[m][sb]overlay={blur_overlay},{v_filter}[vout]"
        else:
            v_filter = f"{v_filter}[vout]"
    else:
        # Khong co subtitle: bo qua ASS, chi xu ly blur neu co
        temp_ass = None
        filter_script_path = os.path.join(task_dir, "ffmpeg_filter_script.txt")
        if blur_sub:
            blur_crop = blur_params["crop"]
            blur_overlay = blur_params["overlay"]
            v_filter = f"split[m][s];[s]crop={blur_crop},{blur_params['blur']}[sb];[m][sb]overlay={blur_overlay}[vout]"
        else:
            v_filter = "null[vout]"

    codec_cfg = get_codec_config(quality, device)

    a_filter = f"[0:a]volume=0.1[orig];[1:a]volume=2[v_tts];[orig][v_tts]amix=inputs=2:duration=first[aout]"
    with open(filter_script_path, "w", encoding='utf-8') as f:
        f.write(f"[0:v]{v_filter};{a_filter}")

    # [WINDOWS FIX] Dùng -filter_complex trực tiếp thay vì -filter_complex_script (deprecated)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_in,
        "-i", combined_audio_file,
        "-filter_complex", f"[0:v]{v_filter};{a_filter}",
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", codec_cfg["codec"],
        "-preset", codec_cfg["preset"],
        "-cq", codec_cfg["cq"],
        "-b:v", codec_cfg["b:v"],
        "-maxrate", codec_cfg["maxrate"],
        "-c:a", "aac", "-b:a", "320k",
        final_output_path
    ]

    subprocess.run(cmd, check=True)
    print(f"[DONE] Video saved: {final_output_path}")

    cleanup_list = [raw_p, filter_script_path, combined_audio_file]
    if temp_ass:
        cleanup_list.append(temp_ass)
    for p in cleanup_list:
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.exists(p):
            os.remove(p)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task_dir", required=True)
    parser.add_argument("--blur", action="store_true")
    parser.add_argument("--output", required=True)
    parser.add_argument("--sub", default=None)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--tts_engine", default="EDGE")
    parser.add_argument("--f0_key", type=float, default=8.0)
    parser.add_argument("--voice_rate", type=float, default=1.5)
    parser.add_argument("--gtts_rate", type=float, default=1.5)
    parser.add_argument("--dvoice_rate", type=float, default=1.1)
    parser.add_argument("--edge_rate", default="+25%")
    parser.add_argument("--neutral_voice", default="vi-VN-Wavenet-C")
    parser.add_argument("--edge_voice", default="vi-VN-HoaiMyNeural")
    parser.add_argument("--quality", default="medium")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--tiktok_voice", default="cutefemale")
    parser.add_argument("--subtitle_position", default="duoi_giua")
    parser.add_argument("--font_size", type=int, default=32)
    parser.add_argument("--margin_v", type=int, default=40)
    parser.add_argument("--blur_start_percent", type=int, default=80)
    parser.add_argument("--blur_end_percent", type=int, default=95)
    parser.add_argument("--aspect_ratio", default="auto")
    parser.add_argument("--font_name", default="Arial")
    parser.add_argument("--font_color", default="#FFFF00")
    parser.add_argument("--outline_color", default="#000000")
    parser.add_argument("--back_color", default="#80000000", help="Màu nền subtitle (#AARRGGBB)")
    parser.add_argument("--blur_intensity", type=int, default=10, help="Độ đậm nhạt blur (0-20)")
    parser.add_argument("--sub_background", default="True", help="Bật/tắt nền phụ đề (True/False)")
    parser.add_argument("--has_subtitle", default="True", help="Co chay TTS+chen phu de hay khong (True/False)")
    args = parser.parse_args()

    SELECT_TYPE = args.tts_engine.upper()
    PITCH = args.f0_key
    VOICE_RATE = args.voice_rate
    GTTSVOICE_RATE = args.gtts_rate
    DVOICE_RATE = args.dvoice_rate
    EDGE_RATE = args.edge_rate
    NEUTRAL_VOICE_ID = args.neutral_voice
    EDGE_VOICE = args.edge_voice
    TIKTOKTTS_SPEED = int(args.dvoice_rate * 10)
    TIKTOKTTS_VOICE = args.tiktok_voice

    init_google_client()
    sub_bg = args.sub_background.lower() in ("true", "1", "yes")
    has_subtitle = args.has_subtitle.lower() in ("true", "1", "yes")
    process_video_only_tts(args.task_dir, args.blur, args.output, args.sub, args.speed,
                           args.quality, args.device,
                           subtitle_position=args.subtitle_position,
                           font_size=args.font_size, margin_v=args.margin_v,
                           blur_start_percent=args.blur_start_percent,
                           blur_end_percent=args.blur_end_percent,
                           blur_intensity=args.blur_intensity,
                           aspect_ratio=args.aspect_ratio, font_name=args.font_name,
                           font_color=args.font_color, outline_color=args.outline_color,
                           back_color=args.back_color,
                           bold=True, sub_background=sub_bg, has_subtitle=has_subtitle)
