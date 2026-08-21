import sys
import argparse
import requests
import json
import time
import itertools
import os
from dotenv import load_dotenv

load_dotenv()


def translate_chunk(chunk_content, api_keys, models, mood, lang):
    lang_map = {
        "zh": "Trung -> Việt",
        "en": "Anh -> Việt",
        "ja": "Nhật -> Việt",
        "ko": "Hàn -> Việt"
    }
    lang_desc = lang_map.get(lang, f"tiếng {lang} sang tiếng Việt")

    prompt_text = f"""
Nhiệm vụ: dịch ({lang_desc}).
YÊU CẦU BẮT BUỘC:
1. Dịch TOÀN BỘ nội dung được cung cấp, không được bỏ sót bất kỳ dòng nào.
2. GIỮ NGUYÊN ĐỊNH DẠNG [hh:mm:ss,mmm] ở đầu dòng không được phép sửa.
3. Không được tóm tắt, Không được dừng lại cho đến khi gặp dòng cuối cùng của văn bản gốc.
4. Trả về văn bản thô, không nằm trong khối code (markdown).
5. Đơn vị tiền tệ phải đổi thành tiền Việt Nam

Nội dung cần dịch:
{chunk_content}
"""

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

    pairs = list(itertools.product(api_keys, models))
    cycle = itertools.cycle(pairs)
    hard_limit = len(pairs) * 3
    attempt = 0

    while attempt < hard_limit:
        api_key, model = next(cycle)
        attempt += 1
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        try:
            print(f"[AI_LOG] [{attempt}/{hard_limit}] Key: {api_key[:8]}... | Model: {model}")
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            res_data = response.json()

            if response.status_code == 200:
                translated_text = res_data['candidates'][0]['content']['parts'][0]['text']
                clean_text = translated_text.replace('```', '').replace('markdown', '').strip()
                print(f"[AI_LOG] OK | Key: {api_key[:8]}... | Model: {model}")
                return clean_text
            elif response.status_code == 429:
                print(f"[AI_RETRY] 429 quota | Key {api_key[:8]}... -> doi cap...")
                time.sleep(2)
            elif response.status_code in (500, 503):
                print(f"[AI_RETRY] Server loi {response.status_code} -> thu lai sau 3s...")
                time.sleep(3)
            else:
                print(f"[AI_ERROR] HTTP {response.status_code} | Key {api_key[:8]}... -> thu tiep...")
                time.sleep(1)
        except Exception as e:
            print(f"[AI_ERROR] Loi ket noi: {e} -> thu lai sau 2s...")
            time.sleep(2)

    print(f"[AI_FATAL] Da thu {hard_limit} lan, tat ca key/model deu that bai.")
    return None


def process_ai_translation(input_file, output_file, mood, lang):
    # Đọc API keys và models từ file .env
    api_keys_str = os.getenv("GEMINI_API_KEYS", "")
    api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]

    models_str = os.getenv("GEMINI_MODELS", "")
    models = [m.strip() for m in models_str.split(",") if m.strip()]

    if not api_keys or not models:
        print("[AI_FATAL] Thiếu GEMINI_API_KEYS hoặc GEMINI_MODELS trong file .env")
        sys.exit(1)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines:
            print("[AI_ERROR] File đầu vào trống.")
            return

        chunk_size = 60
        all_translated_parts = []
        total_lines = len(lines)

        print(f"[AI_LOG] Bắt đầu dịch {total_lines} dòng (mỗi đoạn {chunk_size} dòng)...")

        for i in range(0, total_lines, chunk_size):
            current_chunk = "".join(lines[i:i + chunk_size])
            print(f"[AI_LOG] Đang xử lý đoạn: {i} đến {min(i + chunk_size, total_lines)}")

            result = translate_chunk(current_chunk, api_keys, models, mood, lang)
            if result:
                all_translated_parts.append(result)
                time.sleep(1)
            else:
                print("[AI_FATAL] Không thể dịch đoạn này.")
                sys.exit(1)

        final_content = "\n".join(all_translated_parts)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_content)

        print(f"[AI_LOG] HOÀN THÀNH TOÀN BỘ. Kết quả: {output_file}")
    except Exception as e:
        print(f"[AI_ERROR] Lỗi file: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mood", default="tự nhiên")
    parser.add_argument("--lang", default="zh")
    args = parser.parse_args()
    process_ai_translation(args.input, args.output, args.mood, args.lang)