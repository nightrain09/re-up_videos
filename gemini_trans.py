import sys
import argparse
import requests
import json
import hashlib
import re
import time
import itertools
import os
from dotenv import load_dotenv

from utils.task_progress import (
    atomic_write_text,
    empty_progress,
    load_progress_file,
    save_progress_file,
)

load_dotenv()

# AI phai boc ban dich trong cap marker nay. Chi noi dung giua 2 marker duoc ghi ra file.
BLOCK_START = "<<<TRANSLATION_START>>>"
BLOCK_END = "<<<TRANSLATION_END>>>"

TIMESTAMP_LINE_RE = re.compile(r"^(\[\d{2}:\d{2}:\d{2},\d{3}\])\s+(\S.*)$")

CONFIG_FILE_NAME = "automation_config.json"
DEFAULT_MAX_RETRIES = 5


def _strip_code_fence(content):
    """Bo mot cap ``` bao ngoai khoi, khong dung den ``` nam trong cau."""
    lines = content.splitlines()
    if len(lines) >= 2 and lines[0].strip().startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return content


def extract_translation_block(raw_text):
    """Boc noi dung giua BLOCK_START/BLOCK_END.

    Tra ve (content, None) neu hop le, (None, ly_do) neu sai dinh dang.
    Chi chap nhan dung mot cap marker; chu thua ben ngoai khoi bi bo qua.
    """
    if not raw_text or not raw_text.strip():
        return None, "response rong"

    starts = list(re.finditer(re.escape(BLOCK_START), raw_text, re.IGNORECASE))
    ends = list(re.finditer(re.escape(BLOCK_END), raw_text, re.IGNORECASE))

    if not starts:
        return None, f"thieu marker {BLOCK_START}"
    if not ends:
        return None, f"thieu marker {BLOCK_END}"
    if len(starts) > 1 or len(ends) > 1:
        return None, f"thua marker ({len(starts)} START / {len(ends)} END)"
    if starts[0].start() > ends[0].start():
        return None, "marker END dung truoc START"

    prefix = raw_text[:starts[0].start()].strip()
    suffix = raw_text[ends[0].end():].strip()
    if prefix or suffix:
        print("[AI_WARN] Bo qua van ban nam ngoai khoi dich.")

    content = raw_text[starts[0].end():ends[0].start()].strip()
    content = _strip_code_fence(content)
    if not content:
        return None, "khoi dich rong"
    return content, None


def expected_timestamps(chunk_content):
    """Danh sach timestamp theo thu tu cua cac dong nguon (None neu dong sai format)."""
    timestamps = []
    for line in chunk_content.splitlines():
        line = line.strip()
        if not line:
            continue
        match = TIMESTAMP_LINE_RE.match(line)
        timestamps.append(match.group(1) if match else None)
    return timestamps


def validate_translation(content, expected_ts):
    """Kiem tra so dong va timestamp cua ban dich so voi doan goc."""
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return None, "khoi dich rong"
    if len(lines) != len(expected_ts):
        return None, f"sai so dong: nhan {len(lines)}, can {len(expected_ts)}"

    for index, line in enumerate(lines):
        wanted = expected_ts[index]
        if wanted is None:
            # Dong nguon khong co timestamp (khong xay ra voi output STT) -> chi kiem tra so dong.
            continue
        match = TIMESTAMP_LINE_RE.match(line)
        if not match:
            return None, f"dong {index + 1} thieu/sai timestamp: {line[:60]!r}"
        if match.group(1) != wanted:
            return None, f"timestamp dong {index + 1} lech: nhan {match.group(1)}, can {wanted}"

    return "\n".join(lines), None


def _extract_response_text(res_data):
    """Lay text tu response Gemini, tra ve (text, loi) neu response khong dung duoc."""
    if not isinstance(res_data, dict):
        return None, "JSON tra ve khong hop le"

    candidates = res_data.get("candidates") or []
    if not candidates:
        feedback = res_data.get("promptFeedback") or {}
        reason = feedback.get("blockReason")
        detail = f" (blockReason={reason})" if reason else ""
        return None, f"khong co candidates{detail}"

    candidate = candidates[0]
    finish = candidate.get("finishReason")
    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()

    if finish == "MAX_TOKENS":
        return None, "bi cat do MAX_TOKENS"
    if not text:
        return None, f"response rong (finishReason={finish})"
    return text, None


def build_prompt(chunk_content, lang_desc, correction=None):
    prompt_text = f"""
Nhiệm vụ: dịch ({lang_desc}).
YÊU CẦU BẮT BUỘC:
1. Dịch TOÀN BỘ nội dung được cung cấp, không được bỏ sót bất kỳ dòng nào.
2. GIỮ NGUYÊN timestamp [hh:mm:ss,mmm] ở đầu mỗi dòng, đúng số dòng và đúng thứ tự như bản gốc.
3. Không được tóm tắt, không được dừng lại cho đến khi gặp dòng cuối cùng của văn bản gốc.
4. Bọc TOÀN BỘ bản dịch trong đúng hai dòng đánh dấu sau:
{BLOCK_START}
<nội dung dịch>
{BLOCK_END}
Không viết thêm bất kỳ chữ nào (lời mở đầu, giải thích, markdown ```) bên trong hoặc bên ngoài hai dòng đánh dấu.
5. Đơn vị tiền tệ phải đổi thành tiền Việt Nam.

Nội dung cần dịch:
{chunk_content}
"""
    if correction:
        prompt_text += (
            f"\nLƯU Ý: lần trả lời trước SAI ĐỊNH DẠNG ({correction}). "
            f"Hãy trả lại toàn bộ bản dịch, chỉ nằm giữa {BLOCK_START} và {BLOCK_END}, "
            "đúng số dòng và timestamp như bản gốc.\n"
        )
    return prompt_text


def translate_chunk(chunk_content, api_keys, models, mood, lang, max_retries):
    lang_map = {
        "zh": "Trung -> Việt",
        "en": "Anh -> Việt",
        "ja": "Nhật -> Việt",
        "ko": "Hàn -> Việt"
    }
    lang_desc = lang_map.get(lang, f"tiếng {lang} sang tiếng Việt")

    expected_ts = expected_timestamps(chunk_content)
    if not expected_ts:
        print("[AI_ERROR] Doan khong co dong hop le de dich.")
        return None

    pairs = list(itertools.product(api_keys, models))
    cycle = itertools.cycle(pairs)
    transport_limit = max(1, len(pairs) * 3)
    transport_failures = 0
    format_failures = 0
    last_error = None
    attempt = 0
    retry_label = "∞" if max_retries is None else str(max_retries)

    while True:
        # max_retries = so lan thu lai sau lan sai dinh dang dau tien.
        if max_retries is not None and format_failures > max_retries:
            print(f"[AI_FATAL] Da thu lai {max_retries} lan nhung AI van sai dinh dang.")
            return None

        api_key, model = next(cycle)
        attempt += 1
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        prompt_text = build_prompt(chunk_content, lang_desc, last_error)

        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192,
                "topP": 0.8,
                "topK": 40
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }
        headers = {'Content-Type': 'application/json'}

        try:
            print(
                f"[AI_LOG] [call {attempt}] Key: {api_key[:8]}... | Model: {model} | "
                f"format-retry: {format_failures}/{retry_label}"
            )
            response = requests.post(url, headers=headers, json=payload, timeout=60)

            if response.status_code == 200:
                transport_failures = 0
                try:
                    res_data = response.json()
                except ValueError:
                    res_data = None

                raw_text, extract_error = _extract_response_text(res_data)
                if raw_text is None:
                    format_failures += 1
                    last_error = extract_error
                    print(f"[AI_FORMAT] {extract_error} | Key: {api_key[:8]}... -> thu lai...")
                    time.sleep(1)
                    continue

                content, format_error = extract_translation_block(raw_text)
                if content is not None:
                    content, format_error = validate_translation(content, expected_ts)

                if content is not None:
                    print(f"[AI_LOG] OK | Key: {api_key[:8]}... | Model: {model}")
                    return content

                format_failures += 1
                last_error = format_error
                snippet = raw_text.replace("\n", "⏎")[:120]
                print(
                    f"[AI_FORMAT] {format_error} | response: {snippet} | "
                    f"Key: {api_key[:8]}... -> thu lai..."
                )
                time.sleep(1)
                continue

            transport_failures += 1
            if response.status_code == 429:
                print(f"[AI_RETRY] 429 quota | Key {api_key[:8]}... -> doi cap...")
                time.sleep(2)
            elif response.status_code in (500, 503):
                print(f"[AI_RETRY] Server loi {response.status_code} -> thu lai sau 3s...")
                time.sleep(3)
            else:
                print(f"[AI_ERROR] HTTP {response.status_code} | Key {api_key[:8]}... -> thu tiep...")
                time.sleep(1)

            if transport_failures >= transport_limit:
                print(f"[AI_FATAL] Loi ket noi/quota {transport_failures} lan lien tiep, da xoay het key/model.")
                return None

        except Exception as e:
            transport_failures += 1
            print(f"[AI_ERROR] Loi ket noi: {e} -> thu lai sau 2s...")
            time.sleep(2)
            if transport_failures >= transport_limit:
                print(f"[AI_FATAL] Loi ket noi {transport_failures} lan lien tiep, da xoay het key/model.")
                return None


def _normalize_max_retries(value):
    """0 hoac -1 = vo tan (None); so duong = so lan thu lai."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        print(f"[AI_WARN] gemini_max_retries khong hop le ({value!r}), dung mac dinh {DEFAULT_MAX_RETRIES}.")
        return DEFAULT_MAX_RETRIES
    if value in (0, -1):
        return None
    if value < 0:
        print(f"[AI_WARN] gemini_max_retries khong hop le ({value}), dung mac dinh {DEFAULT_MAX_RETRIES}.")
        return DEFAULT_MAX_RETRIES
    return value


def _config_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE_NAME)


def load_max_retries(cli_value=None):
    if cli_value is not None:
        return _normalize_max_retries(cli_value)

    value = DEFAULT_MAX_RETRIES
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            config = json.load(f)
        if isinstance(config, dict) and "gemini_max_retries" in config:
            value = config["gemini_max_retries"]
    except (OSError, ValueError):
        pass
    return _normalize_max_retries(value)


def process_ai_translation(input_file, output_file, mood, lang, max_retries, progress_file=None):
    # Đọc API keys và models từ file .env
    api_keys_str = os.getenv("GEMINI_API_KEYS", "")
    api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]

    models_str = os.getenv("GEMINI_MODELS", "")
    models = [m.strip() for m in models_str.split(",") if m.strip()]

    if not api_keys or not models:
        print("[AI_FATAL] Thiếu GEMINI_API_KEYS hoặc GEMINI_MODELS trong file .env")
        sys.exit(1)

    progress_file = progress_file or (output_file + ".progress.json")
    retry_label = "vô tận" if max_retries is None else f"{max_retries} lần"
    print(f"[AI_LOG] Retry khi sai định dạng: {retry_label} (gemini_max_retries).")

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines()]
        lines = [line for line in lines if line]

        if not lines:
            print("[AI_ERROR] File đầu vào trống.")
            return

        chunk_size = 60
        total_lines = len(lines)
        total_chunks = (total_lines + chunk_size - 1) // chunk_size
        input_hash = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()

        # Nạp checkpoint; chỉ dùng lại chunk nếu đúng input + chunk_size.
        progress = load_progress_file(progress_file) or empty_progress()
        translate_state = progress.setdefault("stages", {}).setdefault(
            "translate", {"done": False}
        )
        stored_chunks = translate_state.get("chunks") or []
        same_input = (
            translate_state.get("mode") == "GEMINI"
            and translate_state.get("input_hash") == input_hash
            and translate_state.get("chunk_size") == chunk_size
            and translate_state.get("total_lines") == total_lines
        )

        validated_chunks = []
        if same_input and isinstance(stored_chunks, list):
            for index, chunk_text in enumerate(stored_chunks[:total_chunks]):
                if not isinstance(chunk_text, str):
                    break
                start = index * chunk_size
                source_chunk = "\n".join(lines[start:start + chunk_size])
                content, error = validate_translation(
                    chunk_text, expected_timestamps(source_chunk)
                )
                if content is None:
                    print(
                        f"[AI_WARN] Checkpoint chunk {index + 1} không hợp lệ "
                        f"({error}) -> dịch lại từ đây."
                    )
                    break
                validated_chunks.append(content)
        stored_chunks = validated_chunks

        translate_state.update({
            "mode": "GEMINI",
            "done": False,
            "input_hash": input_hash,
            "chunk_size": chunk_size,
            "total_lines": total_lines,
            "chunks": stored_chunks,
        })
        save_progress_file(progress_file, progress)

        done_chunks = len(stored_chunks)
        if done_chunks:
            print(
                f"[AI_LOG] Resume translate từ chunk {done_chunks + 1}/{total_chunks} "
                f"(đã xong {done_chunks} chunk)."
            )

        print(f"[AI_LOG] Bắt đầu dịch {total_lines} dòng (mỗi đoạn {chunk_size} dòng)...")

        for chunk_index in range(done_chunks, total_chunks):
            i = chunk_index * chunk_size
            current_chunk = "\n".join(lines[i:i + chunk_size])
            print(
                f"[AI_LOG] Đang xử lý chunk {chunk_index + 1}/{total_chunks} "
                f"(dòng {i} đến {min(i + chunk_size, total_lines)})"
            )

            result = translate_chunk(current_chunk, api_keys, models, mood, lang, max_retries)
            if not result:
                print("[AI_FATAL] Không thể dịch đoạn này. Giữ checkpoint để lần sau resume.")
                sys.exit(1)

            stored_chunks.append(result)
            translate_state["chunks"] = stored_chunks
            # Lưu ngay trước khi gọi chunk kế tiếp: mất điện không mất tiến độ.
            save_progress_file(progress_file, progress)
            time.sleep(1)

        final_content = "\n".join(part.strip("\n") for part in stored_chunks) + "\n"
        atomic_write_text(output_file, final_content)

        translate_state["done"] = True
        translate_state["chunks"] = stored_chunks
        save_progress_file(progress_file, progress)

        print(f"[AI_LOG] HOÀN THÀNH TOÀN BỘ. Kết quả: {output_file}")
    except SystemExit:
        raise
    except Exception as e:
        print(f"[AI_ERROR] Lỗi file: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mood", default="tự nhiên")
    parser.add_argument("--lang", default="zh")
    parser.add_argument(
        "--progress", default=None,
        help="File progress.json của task. Mac dinh: <output>.progress.json"
    )
    parser.add_argument(
        "--max-retries", type=int, default=None,
        help="So lan thu lai khi sai dinh dang (0 hoac -1 = vo tan). Mac dinh doc tu automation_config.json."
    )
    args = parser.parse_args()
    process_ai_translation(
        args.input, args.output, args.mood, args.lang,
        load_max_retries(args.max_retries), args.progress,
    )
