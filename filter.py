import os
import random
import json
import re
import argparse


def BoLocMMO(text, mood="tinh_cam"):
    # 1. Từ rác (Fix cứng - Không phân biệt hoa thường)
    rac_tu = {
        "Hắc": "Này", "Cáp": "Hả", "Thoại": "nói", "Bốn phía": "Xung quanh",
        "Khả ái": "dễ thương", "Cực kỳ": "rất là", "Phát sinh": "xảy ra", "Cạc": ""
    }

    # 2. Bộ từ điển kèm xác suất
    mood_config = {
        "tinh_cam": {
            "Ta": {"Anh": 0.4, "em": 0.4, "Tôi": 0.1, "Mình": 0.1},
            "Ngươi": {"em": 0.4, "anh": 0.2, "Cậu": 0.2},
            "Nàng": {"em": 0.7, "tiểu thư": 0.3},
            "Hắn": {"em ấy": 0.5, "anh ấy": 0.5},
            "Lão bà": {"Vợ à": 0.6, "Em yêu": 0.4}
        },
        "hai_huoc": {
            "Ta": {"Tôi": 0.4, "Tui": 0.4, "Bố mày đây": 0.2},
            "Ngươi": {"em": 0.4, "cậu": 0.3, "ông nội": 0.3},
            "Cái gì": {"Cái gì cơ?": 0.5, "Gì dợ?": 0.5},
            "Đúng vậy": {"Chuẩn mẹ luôn": 0.7, "Chính xác": 0.3},
            "Lão tử": {"bố mày đây": 0.8, "tui": 0.2}
        },
        "giang_ho": {
            "Ta": {"bố mày": 0.5, "ta": 0.5},
            "Ngươi": {"Con vợ": 0.4, "Cu": 0.6},
            "Lão tử": {"Bố mày": 0.9, "bố": 0.1},
            "Muốn chết": {"muốn chít": 0.5, "chán sống hả": 0.5},
            "Khốn kiếp": {"tồi quá rồi": 0.5, "đồ chó, đồ mi xi": 0.5}
        },
        "xa_giao": {
            "Ta": {"Tôi": 1.0},
            "Ngươi": {"Bạn": 0.7, "Cưng": 0.3},
            "Vị này": {"Người này": 1.0},
            "Xin hãy": {"Làm ơn": 0.6, "Vui lòng": 0.4}
        }
    }

    # Xóa rác (Không phân biệt hoa thường)
    for k, v in rac_tu.items():
        pattern_rac = re.compile(re.escape(k), re.IGNORECASE)
        text = pattern_rac.sub(v, text)

    # Xử lý danh xưng theo xác suất - Fix: dùng Unicode word boundary
    current_mood_dict = mood_config.get(mood, mood_config["xa_giao"])
    for tu_goc, choices_dict in current_mood_dict.items():
        # Dùng (?<!\w) và (?!\w) thay vì \b để hỗ trợ tiếng Việt
        pattern_word = re.compile(rf'(?<!\w){re.escape(tu_goc)}(?!\w)', re.UNICODE | re.IGNORECASE)

        def random_replacement(match, words=choices_dict):
            word_list = list(words.keys())
            weights = list(words.values())
            return random.choices(word_list, weights=weights, k=1)[0]

        text = pattern_word.sub(random_replacement, text)
    return text


def process_file(input_path, output_path, mood="tinh_cam"):
    if not os.path.exists(input_path):
        return
    dataset_path = "dataset_train.jsonl"

    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    final_lines = []
    collected_data = []
    pattern_time = re.compile(r'(\[\d{2}:\d{2}:\d{2}\])\s*(.*)')

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = pattern_time.match(line)
        if match:
            timestamp = match.group(1)
            content = match.group(2).strip()
            fixed_content = BoLocMMO(content, mood)
            final_lines.append(f"{timestamp} {fixed_content}\n")
            if content != fixed_content:
                collected_data.append({
                    "instruction": f"Style {mood}",
                    "input": content,
                    "output": fixed_content
                })
        else:
            final_lines.append(line + "\n")

    tmp_path = output_path + ".tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        f.writelines(final_lines)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, output_path)

    if collected_data:
        with open(dataset_path, 'a', encoding='utf-8') as f_data:
            for entry in collected_data:
                f_data.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"--- Done! Output: {output_path} ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mood", default="tinh_cam")
    args = parser.parse_args()
    process_file(args.input, args.output, args.mood)