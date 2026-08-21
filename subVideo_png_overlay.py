import os
import sys
import subprocess
import argparse


def get_video_dimensions(video_path):
    """Lay width, height cua video bang ffprobe"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-of", "csv=p=0", video_path],
            capture_output=True, text=True, check=True
        )
        parts = result.stdout.strip().split(",")
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    except Exception as e:
        print(f"[PNG_OVERLAY] Loi doc kich thuoc video: {e}")
    return None, None


def get_best_codec_simple():
    """Phat hien codec phu hop: h264_nvenc neu co GPU, libx264 neu khong"""
    try:
        result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5)
        if "h264_nvenc" in result.stdout:
            return "h264_nvenc"
    except Exception:
        pass
    return "libx264"


def _fmt(n):
    """Format số FFmpeg-safe: giữ nguyên 77.5, nhưng 77.0 → 77"""
    if isinstance(n, float) and n == int(n):
        return str(int(n))
    return str(n)


def apply_png_overlay(input_video, output_video, png_path, pos_x=50, pos_y=10,
                       anchor="center", width_percent=40, start_time=0, end_time=0,
                       opacity=100, full_video=False) -> bool:
    """
    Chen PNG overlay len video.
    Tra ve True neu thanh cong, False neu that bai.
    """
    # Kiem tra input video
    if not os.path.exists(input_video):
        print(f"[PNG_OVERLAY] Khong tim thay video input: {input_video}")
        return False

    # Neu khong co PNG hoac PNG khong ton tai -> copy input sang output nguyen ven
    if not png_path or not os.path.exists(png_path):
        print(f"[PNG_OVERLAY] Khong co file PNG hoac PNG khong ton tai. Copy input sang output (no-op).")
        try:
            subprocess.run(["ffmpeg", "-y", "-i", input_video, "-c", "copy", output_video],
                           check=True, capture_output=True)
            return True
        except Exception as e:
            print(f"[PNG_OVERLAY] Loi copy video: {e}")
            return False

    print(f"[PNG_OVERLAY] Dang xu ly: {os.path.basename(input_video)}")

    # Lay kich thuoc video
    vw, vh = get_video_dimensions(input_video)
    if vw is None or vh is None:
        print(f"[PNG_OVERLAY] Khong the doc kich thuoc video. Copy input sang output.")
        try:
            subprocess.run(["ffmpeg", "-y", "-i", input_video, "-c", "copy", output_video],
                           check=True, capture_output=True)
            return True
        except Exception as e:
            print(f"[PNG_OVERLAY] Loi copy video: {e}")
            return False

    print(f"[PNG_OVERLAY] Kich thuoc video: {vw}x{vh}")

    # Xay dung filter_complex
    # 1. Scale PNG theo width_percent (ho tro toi 500%)
    scale_expr = f"scale=iw*{_fmt(width_percent)}/100:-1,format=rgba"

    # 2. Xu ly opacity neu < 100
    if opacity < 100:
        opacity_val = opacity / 100.0
        scale_expr = f"{scale_expr},colorchannelmixer=aa={_fmt(opacity_val)}"

    # 3. Tinh toa do overlay
    # Trong overlay filter: W/H = main video, w/h (overlay_w/overlay_h) = scaled PNG
    x_expr = f"(W-w)*{_fmt(pos_x)}/100"
    y_expr = f"(H-h)*{_fmt(pos_y)}/100"

    # 4. Xu ly enable (start_time, end_time)
    if full_video:
        enable_expr = ""
    elif end_time > 0:
        enable_expr = f":enable='between(t,{_fmt(start_time)},{_fmt(end_time)})'"
    elif start_time > 0:
        enable_expr = f":enable='gte(t,{_fmt(start_time)})'"
    else:
        enable_expr = ""

    # Build overlay filter
    overlay_filter = f"overlay={x_expr}:{y_expr}{enable_expr}"

    # Filter complex
    filter_complex = f"[1:v]{scale_expr}[wm];[0:v][wm]{overlay_filter},format=yuv420p[vout]"

    # Chon codec
    codec = get_best_codec_simple()

    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-i", png_path,
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "0:a?",
        "-c:v", codec,
        "-preset", "p4" if codec == "h264_nvenc" else "medium",
        "-cq", "23",
        "-c:a", "copy",
        output_video
    ]

    try:
        print(f"[PNG_OVERLAY] Dang chay FFmpeg overlay...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if os.path.exists(output_video):
            print(f"[PNG_OVERLAY] Hoan thanh: {os.path.basename(output_video)}")
            return True
        else:
            print(f"[PNG_OVERLAY] Loi: file output khong duoc tao.")
            return False
    except subprocess.CalledProcessError as e:
        print(f"[PNG_OVERLAY] FFmpeg error: {e.stderr}")
        return False
    except Exception as e:
        print(f"[PNG_OVERLAY] Loi: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chen PNG overlay len video")
    parser.add_argument("--input", required=True, help="Duong dan video dau vao")
    parser.add_argument("--output", required=True, help="Duong dan video dau ra")
    parser.add_argument("--png", default=None, help="Duong dan file PNG (ho tro alpha)")
    parser.add_argument("--pos_x", type=float, default=50, help="% vi tri ngang (0-100)")
    parser.add_argument("--pos_y", type=float, default=10, help="% vi tri doc (0-100)")
    parser.add_argument("--anchor", default="center", choices=["top_left", "center"],
                        help="Goc tinh toa do")
    parser.add_argument("--width_percent", type=float, default=40, help="% chieu rong PNG so voi video (0-500)")
    parser.add_argument("--start_time", type=float, default=0, help="Giay bat dau hien overlay")
    parser.add_argument("--end_time", type=float, default=0, help="Giay ket thuc (0 = den het video)")
    parser.add_argument("--opacity", type=float, default=100, help="Do mo 0-100")
    parser.add_argument("--full_video", action="store_true", help="Keo dai overlay toan bo video (bo qua start/end time)")

    args = parser.parse_args()

    success = apply_png_overlay(
        input_video=args.input,
        output_video=args.output,
        png_path=args.png,
        pos_x=args.pos_x,
        pos_y=args.pos_y,
        anchor=args.anchor,
        width_percent=args.width_percent,
        start_time=args.start_time,
        end_time=args.end_time,
        opacity=args.opacity,
        full_video=args.full_video
    )

    sys.exit(0 if success else 1)