import collections
import os
import argparse
import sys

# Fix cho Python 3.10+
if not hasattr(collections, 'MutableSet'):
    import collections.abc
    collections.MutableSet = collections.abc.MutableSet
    collections.Mapping = collections.abc.Mapping
    collections.MutableMapping = collections.abc.MutableMapping
    collections.Iterable = collections.abc.Iterable
    collections.MutableSequence = collections.abc.MutableSequence

from faster_whisper import WhisperModel

try:
    from moviepy.editor import VideoFileClip
except ImportError:
    from moviepy import VideoFileClip

# Cache model to avoid reloading
_MODEL_CACHE = {}


def get_model(model_size="small", device="cuda"):
    key = f"{model_size}_{device}"
    if key not in _MODEL_CACHE:
        print(f"--- Initializing Whisper {device} ({model_size})... ---")
        _MODEL_CACHE[key] = WhisperModel(model_size, device=device, compute_type="int8")
    return _MODEL_CACHE[key]


def format_timestamp(seconds):
    ms = int((seconds - int(seconds)) * 1000)
    full_seconds = int(seconds)
    hours = full_seconds // 3600
    minutes = (full_seconds % 3600) // 60
    secs = full_seconds % 60
    return f"[{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}]"


def process_video(input_path, output_path, device="cuda", language="zh", model_size="small"):
    audio_temp = f"{input_path}_temp.mp3"

    print(f"--- 1. Extracting audio from {input_path}... ---")
    try:
        video = VideoFileClip(input_path)
        video.audio.write_audiofile(audio_temp, logger=None)
    except Exception as e:
        print(f"ERROR Moviepy: {e}")
        return

    print(f"--- 2. Loading Whisper {device} ({model_size})... ---")
    try:
        model = get_model(model_size, device)
    except Exception as e:
        print(f"ERROR loading model: {e}")
        return

    print(f"--- 3. Transcribing (Language: {language})... ---")
    segments, info = model.transcribe(
        audio_temp,
        language=language,
        vad_filter=True,
        beam_size=8
    )

    print(f"--- 4. Writing results to {output_path}... ---")
    with open(output_path, "w", encoding="utf-8") as f:
        for segment in segments:
            ts_str = format_timestamp(segment.start)
            text = segment.text.strip()
            if text:
                line = f"{ts_str} {text}"
                f.write(line + "\n")
                print(f"[STT] {line}")

    video.close()
    if os.path.exists(audio_temp):
        os.remove(audio_temp)
    print("--- DONE ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Whisper STT")
    parser.add_argument("--input", required=True, help="Input video path")
    parser.add_argument("--output", required=True, help="Output txt path")
    parser.add_argument("--device", default="cuda", help="Device: cuda or cpu")
    parser.add_argument("--lang", default="zh", help="Source language")
    parser.add_argument("--model", default="small", help="Model size: tiny/base/small/medium/large-v3")
    args = parser.parse_args()

    if os.path.exists(args.input):
        process_video(args.input, args.output, args.device, args.lang, args.model)
    else:
        print(f"ERROR: File not found {args.input}")
        sys.exit(1)