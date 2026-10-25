import hashlib
import json
import os
from datetime import datetime


PROGRESS_VERSION = 1

# Thứ tự stage trong pipeline.
STAGE_ORDER = ["stt", "translate", "filter", "preprocess", "png_overlay", "render"]

# reset stage X thì các stage phụ thuộc cũng phải làm lại.
DEPENDENTS = {
    "stt": ["translate", "filter", "render"],
    "translate": ["filter", "render"],
    "filter": ["render"],
    "preprocess": ["png_overlay", "render"],
    "png_overlay": ["render"],
}

# Chỉ các key này ảnh hưởng tới nội dung video. Thay đổi chúng => làm lại task.
FINGERPRINT_KEYS = [
    "trans_engine", "source_lang", "mood", "stt_model",
    "voice_type", "rvc_model", "rvc_base", "rvc_mode",
    "edge_voice", "neutral_voice", "tiktok_voice",
    "voice_rate", "gtts_rate", "dvoice_rate", "edge_rate", "f0_key",
    "speed", "quality", "audio_mode", "bgm_file",
    "brightness", "cut_start", "cut_end",
    "blur_sub", "subtitle_position", "font_size", "margin_v",
    "blur_start_percent", "blur_end_percent", "blur_intensity",
    "aspect_ratio", "font_name", "font_color", "outline_color",
    "sub_background", "back_color", "has_subtitle",
    "enable_png_overlay", "png_path", "png_pos_x", "png_pos_y",
    "png_anchor", "png_width_percent", "png_start_time", "png_end_time",
    "png_full_video",
]


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def progress_path(task_dir):
    return os.path.join(task_dir, "progress.json")


def load_progress_file(path):
    """Đọc progress; trả None nếu file thiếu, hỏng hoặc sai version."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("version") != PROGRESS_VERSION:
        return None
    if not isinstance(data.get("stages"), dict):
        return None
    return data


def load_progress(task_dir):
    return load_progress_file(progress_path(task_dir))


def atomic_write_json(path, data):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def atomic_write_text(path, text):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def save_progress_file(path, data):
    data["updated_at"] = _now()
    atomic_write_json(path, data)
    return data


def save_progress(task_dir, data):
    return save_progress_file(progress_path(task_dir), data)


def empty_progress(task_id="", config_fp=None, source=None):
    now = _now()
    return {
        "version": PROGRESS_VERSION,
        "task_id": task_id,
        "created_at": now,
        "updated_at": now,
        "fingerprint": {"config": config_fp, "source": source or {}},
        "stages": {name: {"done": False} for name in STAGE_ORDER},
    }


def fingerprint_config(cfg):
    """Hash các key config ảnh hưởng tới nội dung video."""
    raw = json.dumps(
        {key: cfg.get(key) for key in FINGERPRINT_KEYS},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def source_identity(path):
    """Danh tính nhẹ của video nguồn: size + mtime (không hash cả file)."""
    try:
        stat = os.stat(path)
        return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    except OSError:
        return {}


def fingerprint_matches(progress, config_fp, source):
    """So fingerprint hiện tại với progress. Config rỗng => bỏ qua kiểm tra."""
    fingerprint = (progress or {}).get("fingerprint") or {}
    if config_fp and fingerprint.get("config") != config_fp:
        return False
    old_source = fingerprint.get("source") or {}
    if source and old_source and old_source != source:
        return False
    return True


def get_stage(progress, stage):
    stages = progress.setdefault("stages", {})
    value = stages.get(stage)
    if not isinstance(value, dict):
        value = {"done": False}
        stages[stage] = value
    return value


def stage_done(progress, stage):
    return bool(get_stage(progress, stage).get("done"))


def mark_done(progress, stage, **fields):
    data = get_stage(progress, stage)
    data.update(fields)
    data["done"] = True
    return data


def reset_from(progress, stage):
    """Reset stage + toàn bộ stage phụ thuộc; trả về set tên các stage bị reset."""
    reset = set()

    def _walk(name):
        if name in reset:
            return
        reset.add(name)
        for child in DEPENDENTS.get(name, []):
            _walk(child)

    _walk(stage)
    stages = progress.setdefault("stages", {})
    for name in reset:
        stages[name] = {"done": False}
    return reset
