import re
import os


def parse_txt(txt_path):
    """Đọc file subtitle định dạng [HH:MM:SS,mmm] text"""
    if not os.path.exists(txt_path):
        return []
    subs = []
    pattern = re.compile(r'\[(\d{1,2}):(\d{2}):(\d{2}),(\d{3})\]\s*(.*)')
    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                h, m, s, ms_part = map(int, match.groups()[:4])
                ms = (h * 3600 + m * 60 + s) * 1000 + ms_part
                subs.append({'start_ms': ms, 'text': match.group(5)})
    return subs


def ms_to_ass_time(ms):
    """Chuyển milliseconds sang định dạng ASS: HH:MM:SS.cs"""
    total_seconds = max(0, ms) / 1000.0
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    s = int(total_seconds % 60)
    cs = int((ms % 1000) // 10)
    return f"{h:02d}:{m:02d}:{s:02d}.{cs:02d}"


def hex_to_ass_color(hex_color):
    """Chuyển mã màu hex (#RRGGBB hoặc #AARRGGBB) sang ASS color (&HAABBGGRR)

    Lưu ý: ASS dùng alpha ngược - 00 = opaque, FF = transparent
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        # Không có alpha, mặc định 00 = hiện hoàn toàn
        r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
        a = "00"
    elif len(hex_color) == 8:
        a, r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6], hex_color[6:8]
        # Đảo ngược alpha: FF -> 00, 00 -> FF, 80 -> 7F, ...
        a = format(255 - int(a, 16), '02X')
    else:
        return "&H00FFFF00&"  # màu vàng mặc định, opaque

    # ASS format: &HAABBGGRR
    return f"&H{a}{b}{g}{r}&"


def generate_ass(events, output_path, font_size=32, alignment=2, margin_v=40, margin_l=10, margin_r=10,
                 font_name="Arial", font_color="#FFFF00", outline_color="#000000", back_color="#80000000", bold=True,
                 border_style=1, outline=3, shadow=0):
    """Tạo file .ass từ danh sách events với style tùy chỉnh

    Args:
        alignment: 1=bottom-left, 2=bottom-center, 3=bottom-right
                   4=mid-left, 5=mid-center, 6=mid-right
                   7=top-left, 8=top-center, 9=top-right
        font_name: Tên font hoặc đường dẫn tới file .ttf
        font_color: Màu chữ dạng hex (#RRGGBB hoặc #AARRGGBB)
        outline_color: Màu viền dạng hex
        back_color: Màu nền dạng hex (#AARRGGBB), mặc định đen bán trong suốt
        bold: True=đậm, False=không đậm
        border_style: 1=outline + shadow, 3=background box (để hiện nền phía sau chữ)
        outline: Độ dày viền (chỉ dùng khi border_style=1)
        shadow: Độ dày bóng đổ (chỉ dùng khi border_style=1)
    """
    # Nếu font_name là đường dẫn file .ttf, dùng tên file làm font name
    if font_name.lower().endswith('.ttf'):
        font_name = os.path.splitext(os.path.basename(font_name))[0]

    primary = hex_to_ass_color(font_color)       # Màu chữ
    outline = hex_to_ass_color(outline_color)     # Màu viền
    back = hex_to_ass_color(back_color)           # Màu nền
    bold_flag = "1" if bold else "0"

    with open(output_path, "w", encoding='utf-8') as f:
        f.write(
            "[Script Info]\nScriptType: v4.00+\nPlayResX: 384\nPlayResY: 640\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Default,{font_name},{font_size},{primary},&H000000FF,{outline},{back},{bold_flag},0,0,0,100,100,0,0,{border_style},{outline},{shadow},{alignment},{margin_l},{margin_r},{margin_v},1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            + "\n".join(events)
        )
