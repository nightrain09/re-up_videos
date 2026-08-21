"""Cấu hình vị trí subtitle & blur theo tỷ lệ video và loại video - Hỗ trợ blur %, aspect ratio tùy chọn, font, màu chữ"""
import json
import os

# === Định nghĩa vị trí subtitle chi tiết ===
# alignment: 1=dưới trái, 2=dưới giữa, 3=dưới phải
#             4=giữa trái, 5=giữa, 6=giữa phải
#             7=trên trái, 8=trên giữa, 9=trên phải
SUBTITLE_POSITIONS = {
    "duoi_giua":   {"alignment": 2, "desc": "Dưới giữa"},
    "duoi_trai":   {"alignment": 1, "desc": "Dưới trái"},
    "duoi_phai":   {"alignment": 3, "desc": "Dưới phải"},
    "giua_giua":   {"alignment": 5, "desc": "Giữa màn hình"},
    "tren_giua":   {"alignment": 8, "desc": "Trên giữa"},
    "tren_trai":   {"alignment": 7, "desc": "Trên trái"},
    "tren_phai":   {"alignment": 9, "desc": "Trên phải"}
}

CONFIG_FILE = "subtitle_config.json"


def detect_aspect_ratio(width, height):
    """Phát hiện tỷ lệ video từ kích thước"""
    if width > height:
        ratio = round(width / height, 2)
        if abs(ratio - 16/9) < 0.1:
            return "16:9"
        elif abs(ratio - 4/3) < 0.1:
            return "4:3"
        else:
            return "16:9"
    else:
        ratio = round(height / width, 2)
        if abs(ratio - 16/9) < 0.1:
            return "9:16"
        elif abs(ratio - 4/3) < 0.1:
            return "3:4"
        else:
            return "9:16"


def get_blur_filter_params(blur_start_percent=80, blur_end_percent=95, blur_intensity=10):
    """Tính tham số blur dựa trên % bắt đầu và % kết thúc

    Args:
        blur_start_percent: % từ trên xuống để bắt đầu blur (0-100)
        blur_end_percent: % từ trên xuống để kết thúc blur (0-100)
        blur_intensity: độ đậm nhạt blur (0-20), giá trị càng cao càng mờ

    Returns:
        dict với keys "crop", "overlay", và "blur" cho ffmpeg
    """
    blur_h = f"ih*{(blur_end_percent - blur_start_percent)/100}"
    blur_y = f"ih*{blur_start_percent/100}"

    # boxblur giới hạn chroma radius <= 15, luma radius không giới hạn
    # Dùng cú pháp boxblur=luma_radius:chroma_radius để set riêng, cap chroma ở 15
    chroma_radius = min(blur_intensity, 15)
    
    return {
        "crop": f"iw:{blur_h}:0:{blur_y}",
        "overlay": f"0:H*{blur_start_percent/100}",
        "blur": f"boxblur={blur_intensity}:{chroma_radius}"
    }


def get_profile(aspect_ratio, position_key="duoi_giua", font_size=32, margin_v=40,
                blur_start_percent=80, blur_end_percent=95):
    """Lấy profile cho tỷ lệ video với các thông số tùy chỉnh"""
    pos = SUBTITLE_POSITIONS.get(position_key, SUBTITLE_POSITIONS["duoi_giua"])
    return {
        "alignment": pos["alignment"],
        "font_size": font_size,
        "margin_v": margin_v,
        "blur_start_percent": blur_start_percent,
        "blur_end_percent": blur_end_percent
    }


def save_config(config_data):
    """Lưu cấu hình user vào file JSON chuyên dụng"""
    with open(CONFIG_FILE, "w", encoding='utf-8') as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)
    return True


def load_config():
    """Đọc cấu hình user từ file JSON, trả về dict rỗng nếu chưa có"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def get_subtitle_alignment_from_blur(blur_start_percent, blur_end_percent):
    """Tự động xác định vị trí phụ đề dựa trên vùng blur

    Phụ đề sẽ được đặt vào chính vùng bị làm mờ.
    Nếu blur ở dưới -> sub ở dưới, blur ở trên -> sub ở trên, blur ở giữa -> sub ở giữa.
    """
    blur_center = (blur_start_percent + blur_end_percent) / 2
    if blur_center >= 65:   # vùng blur ở 1/3 dưới video
        return 2            # bottom-center
    elif blur_center <= 35: # vùng blur ở 1/3 trên video
        return 8            # top-center
    else:                   # vùng blur ở giữa
        return 5            # mid-center


def get_subtitle_margin_from_blur(blur_start_percent, blur_end_percent, alignment, font_size=32, playres_y=640):
    """Tính margin_v để subtitle nằm chính xác trong vùng blur

    ASS PlayResY mặc định là 640. Tính pixel position rồi map về margin_v.
    
    Args:
        blur_start_percent: % từ trên xuống bắt đầu blur (0-100)
        blur_end_percent: % từ trên xuống kết thúc blur (0-100)
        alignment: ASS alignment (2=bottom, 5=mid, 8=top)
        font_size: kích thước font (dùng để căn chỉnh khoảng cách)
        playres_y: chiều cao ASS (mặc định 640)

    Returns:
        margin_v phù hợp để sub nằm trong vùng blur
    """
    blur_start_y = playres_y * blur_start_percent / 100
    blur_end_y = playres_y * blur_end_percent / 100
    blur_height = blur_end_y - blur_start_y
    
    # Khoảng đệm an toàn: tối thiểu 1/2 font_size và tối đa 1/4 blur_height
    padding = min(font_size // 2, int(blur_height * 0.2))
    
    if alignment == 2:  # bottom-center
        # Sub đặt ở bottom của vùng blur
        margin_v = int(playres_y - blur_end_y + padding)
    elif alignment == 8:  # top-center
        # Sub đặt ở top của vùng blur
        margin_v = int(blur_start_y + padding)
    else:  # mid-center (5)
        # Sub đặt giữa vùng blur
        margin_v = 0  # mid alignment tự động căn giữa, không cần margin
    
    return max(margin_v, 0)


def get_subtitle_margin_from_blur_direct(blur_start_percent, blur_end_percent, alignment, font_size=32,
                                          playres_x=384, playres_y=640):
    """Tính margin_v chính xác để sub nằm gọn trong vùng blur, dùng pos filter
    
    Trả về margin_v và margin_l/r cho alignment tương ứng.
    Với bottom alignment, margin_v là khoảng cách từ bottom lên.
    Với top alignment, margin_v là khoảng cách từ top xuống.
    """
    return get_subtitle_margin_from_blur(blur_start_percent, blur_end_percent, alignment, font_size, playres_y)


def get_subtitle_filter(position_key="duoi_giua", font_size=32, margin_v=40, font_name="Arial",
                        font_color="#FFFF00", outline_color="#000000", bold=True):
    """Tạo style override cho ASS subtitle dựa trên vị trí"""
    from .subtitle import hex_to_ass_color
    pos = SUBTITLE_POSITIONS.get(position_key, SUBTITLE_POSITIONS["duoi_giua"])
    alignment = pos["alignment"]
    primary = hex_to_ass_color(font_color)
    outline = hex_to_ass_color(outline_color)
    bold_flag = "1" if bold else "0"
    style = (
        f"Style: Default,{font_name},{font_size},{primary},&H000000FF,{outline},"
        f"&H80000000,{bold_flag},0,0,0,100,100,0,0,"
        f"1,3,0,{alignment},10,10,\"{margin_v}\",1"
    )
    return style