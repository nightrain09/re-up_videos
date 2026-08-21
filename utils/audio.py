import os
import subprocess
import tempfile
from pydub import AudioSegment


def speed_change(seg, rate):
    """Thay đổi tốc độ audio bằng FFmpeg atempo"""
    if rate == 1.0:
        return seg
    if rate < 0.5 or rate > 2.0:
        # FFmpeg atempo giới hạn 0.5-2.0, cần chain filter
        if rate < 0.5:
            return speed_change(speed_change(seg, 0.5), rate / 0.5)
        else:
            return speed_change(speed_change(seg, 2.0), rate / 2.0)

    tmp_in = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    tmp_out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

    try:
        seg.export(tmp_in, format="wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_in, "-filter:a", f"atempo={rate}", "-vn", tmp_out],
            capture_output=True, check=True,
        )
        return AudioSegment.from_file(tmp_out)
    except Exception:
        return seg
    finally:
        for f in [tmp_in, tmp_out]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass


def trim_silence(seg, thresh=-50, padding=50):
    """Cắt bỏ khoảng lặng thừa ở đầu và cuối audio"""
    return seg.strip_silence(silence_thresh=thresh, padding=padding)