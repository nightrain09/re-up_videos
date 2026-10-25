"""
AutomationApp.py - Giao diện CHÍNH cho tự động hóa
Thiết kế lại toàn bộ giao diện (bố cục dạng Tab, theme hiện đại, thẻ nhóm rõ ràng)
Giữ nguyên toàn bộ tên biến / thuộc tính / hàm để không ảnh hưởng tới logic xử lý.
"""
import sys
import os
import json
import shutil
import threading

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QPushButton, QComboBox, QLabel, QGroupBox,
    QRadioButton, QCheckBox, QMessageBox, QSlider, QSpinBox,
    QProgressBar, QTextEdit, QFileDialog, QDialog, QListWidget,
    QColorDialog, QTabWidget, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QIcon, QPixmap
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRect, QSize
from concurrent.futures import ThreadPoolExecutor, as_completed

from MainController import MainController
from utils.task_progress import fingerprint_config, source_identity


CONFIG_FILE = "automation_config.json"

# ============================================================
#  BẢNG MÀU / THEME
# ============================================================
COLOR_BG = "#F4F6FA"
COLOR_CARD = "#FFFFFF"
COLOR_BORDER = "#E2E6ED"
COLOR_TEXT = "#1F2937"
COLOR_MUTED = "#6B7280"
COLOR_PRIMARY = "#4F46E5"
COLOR_PRIMARY_DARK = "#4338CA"
COLOR_ACCENT = "#0EA5A5"
COLOR_WARN = "#F59E0B"
COLOR_DANGER = "#EF4444"
COLOR_SUCCESS = "#22C55E"

APP_STYLESHEET = f"""
QMainWindow {{
    background: {COLOR_BG};
}}
QWidget {{
    color: {COLOR_TEXT};
    font-family: "Segoe UI", "Tahoma", sans-serif;
    font-size: 13px;
}}
QLabel#TitleLabel {{
    font-size: 19px;
    font-weight: 700;
    color: {COLOR_PRIMARY_DARK};
    padding: 4px 0px;
}}
QLabel#SubTitleLabel {{
    font-size: 12px;
    color: {COLOR_MUTED};
    padding-bottom: 6px;
}}
QFrame#Card {{
    background: {COLOR_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
}}
QLabel#CardTitle {{
    font-size: 14px;
    font-weight: 700;
    color: {COLOR_PRIMARY_DARK};
    padding: 0px;
}}
QFrame#CardSep {{
    background: {COLOR_BORDER};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}
QFrame#VSep {{
    background: {COLOR_BORDER};
    border: none;
    max-width: 1px;
    min-width: 1px;
}}
QLabel#SectionLabel {{
    color: {COLOR_MUTED};
    font-weight: 700;
    font-size: 11px;
    padding-top: 4px;
}}
QLabel {{
    color: {COLOR_TEXT};
}}
QLineEdit, QComboBox, QSpinBox {{
    background: #FFFFFF;
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 24px;
}}
QComboBox {{
    min-width: 108px;
}}
QSpinBox {{
    min-width: 70px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {COLOR_PRIMARY};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background: white;
    border: 1px solid {COLOR_BORDER};
    selection-background-color: {COLOR_PRIMARY};
    selection-color: white;
}}
QRadioButton, QCheckBox {{
    spacing: 8px;
    padding: 3px 2px;
}}
QRadioButton::indicator, QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1.5px solid {COLOR_BORDER};
    background: #FFFFFF;
}}
QRadioButton::indicator {{
    border-radius: 9px;
}}
QCheckBox::indicator {{
    border-radius: 4px;
}}
QRadioButton::indicator:hover, QCheckBox::indicator:hover {{
    border: 1.5px solid {COLOR_PRIMARY};
}}
QRadioButton::indicator:checked {{
    border: 1.5px solid {COLOR_PRIMARY};
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 {COLOR_PRIMARY}, stop:0.5 {COLOR_PRIMARY}, stop:0.6 white, stop:1 white);
}}
QCheckBox::indicator:checked {{
    border: 1.5px solid {COLOR_PRIMARY};
    background: {COLOR_PRIMARY};
    image: none;
}}
QRadioButton::indicator:disabled, QCheckBox::indicator:disabled {{
    border: 1.5px solid {COLOR_BORDER};
    background: #F0F1F5;
}}
QSlider {{
    min-width: 110px;
    min-height: 22px;
}}
QSlider::groove:horizontal {{
    height: 5px;
    background: {COLOR_BORDER};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {COLOR_PRIMARY};
    width: 16px;
    height: 16px;
    margin: -7px 0;
    border-radius: 9px;
}}
QSlider::sub-page:horizontal {{
    background: {COLOR_PRIMARY};
    border-radius: 3px;
}}
QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    background: {COLOR_BG};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {COLOR_MUTED};
    padding: 10px 20px;
    margin-right: 4px;
    border-radius: 8px 8px 0 0;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background: {COLOR_CARD};
    color: {COLOR_PRIMARY_DARK};
    border: 1px solid {COLOR_BORDER};
    border-bottom: none;
}}
QTabBar::tab:hover {{
    color: {COLOR_PRIMARY};
}}
QProgressBar {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    background: {COLOR_CARD};
    height: 22px;
    text-align: center;
    font-weight: 600;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLOR_ACCENT}, stop:1 {COLOR_PRIMARY});
    border-radius: 8px;
}}
QTextEdit#LogArea {{
    background-color: #0F172A;
    color: #34D399;
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 12px;
    border-radius: 8px;
    border: 1px solid {COLOR_BORDER};
    padding: 8px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLOR_MUTED};
}}
"""


def _make_card(title_text, icon="", show_title=True):
    """Tạo 1 khối 'card' thay cho QGroupBox để tránh lỗi chồng tiêu đề/nội dung.
    Trả về (frame, body_layout) - body_layout là nơi chứa nội dung bên trong.
    show_title=False: không hiển thị dòng tiêu đề + đường kẻ phân cách phía trên."""
    card = QFrame()
    card.setObjectName("Card")
    outer = QVBoxLayout(card)
    outer.setContentsMargins(18, 16, 18, 18)
    outer.setSpacing(12)

    if show_title:
        head = QLabel(f"{icon}  {title_text}" if icon else title_text)
        head.setObjectName("CardTitle")
        outer.addWidget(head)

        sep = QFrame()
        sep.setObjectName("CardSep")
        sep.setFrameShape(QFrame.Shape.HLine)
        outer.addWidget(sep)

    body = QVBoxLayout()
    body.setContentsMargins(0, 2, 0, 0)
    body.setSpacing(12)
    outer.addLayout(body)

    return card, body


def _push_btn_style(bg, fg="white", radius=6, pad="6px 14px", weight=600):
    return (f"QPushButton {{ background:{bg}; color:{fg}; border:none; "
            f"border-radius:{radius}px; padding:{pad}; font-weight:{weight}; }}"
            f"QPushButton:hover {{ background:{_darken(bg)}; }}"
            f"QPushButton:pressed {{ background:{_darken(bg, 0.85)}; }}"
            f"QPushButton:disabled {{ background:#B7BCC7; color:#EEE; }}")


def _darken(hex_color, factor=0.9):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return hex_color
    r = int(int(hex_color[0:2], 16) * factor)
    g = int(int(hex_color[2:4], 16) * factor)
    b = int(int(hex_color[4:6], 16) * factor)
    return f"#{max(0,min(r,255)):02x}{max(0,min(g,255)):02x}{max(0,min(b,255)):02x}"


def load_saved_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Không thể lưu config: {e}")


def export_config_to_file(config):
    """Xuất cấu hình ra file JSON riêng"""
    path, _ = QFileDialog.getSaveFileName(
        None, "Xuất cấu hình", "config.json", "JSON files (*.json)")
    if path:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            QMessageBox.warning(None, "Lỗi", f"Không thể xuất: {e}")
    return False


def import_config_from_file():
    """Nhập cấu hình từ file JSON"""
    path, _ = QFileDialog.getOpenFileName(
        None, "Nhập cấu hình", "", "JSON files (*.json)")
    if path and os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            QMessageBox.warning(None, "Lỗi", f"Không thể nhập: {e}")
    return None


def get_system_fonts():
    """Lấy danh sách font có sẵn (dùng danh sách tĩnh)"""
    return ["Arial", "Times New Roman", "Tahoma", "Verdana", "Calibri",
            "Roboto", "Noto Sans", "Open Sans", "DejaVu Sans", "Ubuntu",
            "Helvetica", "Courier New", "Georgia", "Trebuchet MS", "Comic Sans MS"]


def _section_label(text):
    lbl = QLabel(text)
    lbl.setObjectName("SectionLabel")
    return lbl


def _wrap_scroll(widget):
    """Bọc 1 widget (trang tab) trong QScrollArea để nội dung luôn đủ chỗ hiển thị,
    tránh bị co ép / chồng lấn khi panel không đủ chiều cao."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidget(widget)
    scroll.setStyleSheet("QScrollArea { background: transparent; }")
    return scroll


# ============================================================
#  WORKER
# ============================================================
class AutomationWorker(QThread):
    LogSignal = pyqtSignal(str)
    ProgressSignal = pyqtSignal(int)
    FinishedSignal = pyqtSignal(int, int)

    def __init__(self, config, controller):
        super().__init__()
        self.config = config
        self.controller = controller
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def _task_is_complete(self, task_id, source_path):
        """Output cuối đã xong và đúng config hiện tại hay chưa."""
        final_name = os.path.join(self.controller.OutputDir, f"{task_id}.mp4")
        if not self.controller._video_ready(final_name):
            return False

        try:
            with open(final_name + ".meta.json", "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, ValueError):
            # Output từ bản cũ chưa có meta -> coi như đã xong.
            return True

        if meta.get("config_fingerprint") != fingerprint_config(self.config):
            return False

        current_source = source_identity(source_path) if source_path else {}
        old_source = meta.get("source") or {}
        if current_source and old_source and current_source != old_source:
            return False
        return True

    def process_one_video(self, task_id, local_path):
        cfg = self.config
        config_fp = fingerprint_config(cfg)
        try:
            result_path = self.controller.ExecuteWorkflow(
                VideoUrl=local_path,
                VoiceType=cfg['voice_type'],
                RvcModel=cfg['rvc_model'] if cfg['voice_type'] == "RVC" else "None",
                RvcBase=cfg['rvc_base'],
                RvcDevice=cfg['rvc_device'],
                AudioMode=cfg['audio_mode'],
                BlurSub=cfg['blur_sub'],
                BgmFile=cfg.get('bgm_file'),
                MoodStyle=cfg['mood'],
                TaskId=task_id,
                TransEngine=cfg['trans_engine'],
                Speed=cfg['speed'],
                Fps=30,
                F0Key=cfg['f0_key'],
                SourceLang=cfg['source_lang'],
                VoiceRate=cfg.get('voice_rate', 1.0),
                GttsRate=cfg.get('gtts_rate', 1.0),
                DVoiceRate=cfg.get('dvoice_rate', 1.0),
                EdgeRate=cfg.get('edge_rate', '+25%'),
                NeutralVoiceId=cfg['neutral_voice'],
                EdgeVoiceId=cfg['edge_voice'],
                SttModel=cfg['stt_model'],
                Quality=cfg['quality'],
                RenderDevice=cfg['render_device'],
                RvcMode=cfg['rvc_mode'],
                SttDevice=cfg.get('stt_device', 'cuda'),
                SttWorkers=cfg['max_concurrent'],
                SubtitlePosition=cfg.get('subtitle_position', 'duoi_giua'),
                FontSize=cfg.get('font_size', 32),
                MarginV=cfg.get('margin_v', 40),
                BlurStartPercent=cfg.get('blur_start_percent', 80),
                BlurEndPercent=cfg.get('blur_end_percent', 95),
                BlurIntensity=cfg.get('blur_intensity', 10),
                AspectRatio=cfg.get('aspect_ratio', 'auto'),
                FontName=cfg.get('font_name', 'Arial'),
                FontColor=cfg.get('font_color', '#FFFF00'),
                OutlineColor=cfg.get('outline_color', '#000000'),
                SubBackground=cfg.get('sub_background', True),
                BackColor=cfg.get('back_color', '#80000000'),
                TikTokVoice=cfg.get('tiktok_voice', 'cutefemale'),
                Brightness=cfg.get('brightness', 0),
                CutStart=cfg.get('cut_start', 0),
                CutEnd=cfg.get('cut_end', 0),
                EnablePngOverlay=cfg.get('enable_png_overlay', False),
                PngPath=cfg.get('png_path', None),
                PngPosX=cfg.get('png_pos_x', 50),
                PngPosY=cfg.get('png_pos_y', 10),
                PngAnchor=cfg.get('png_anchor', 'center'),
                PngWidthPercent=cfg.get('png_width_percent', 40),
                PngStartTime=cfg.get('png_start_time', 0),
                PngEndTime=cfg.get('png_end_time', 0),
                PngFullVideo=cfg.get('png_full_video', False),
                HasSubtitle=cfg.get('has_subtitle', True),
                ConfigFingerprint=config_fp,
            )
            if result_path and os.path.exists(result_path):
                final_name = os.path.join(self.controller.OutputDir, f"{task_id}.mp4")
                final_meta = final_name + ".meta.json"
                result_meta = result_path + ".meta.json"
                if os.path.exists(final_name):
                    os.remove(final_name)
                if os.path.exists(final_meta):
                    os.remove(final_meta)
                os.replace(result_path, final_name)
                if os.path.exists(result_meta):
                    os.replace(result_meta, final_meta)
                self.LogSignal.emit(f"OK {task_id} -> {final_name}")
                return True
            else:
                self.LogSignal.emit(f"FAIL {task_id}")
                return False
        except Exception as e:
            self.LogSignal.emit(f"ERROR {task_id}: {str(e)}")
            return False

    def run(self):
        cfg = self.config
        file_path = cfg['file_path']

        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]

        total = len(urls)
        download_dir = os.path.join(self.controller.BaseDir, "downloaded_videos")
        os.makedirs(download_dir, exist_ok=True)

        self.LogSignal.emit(f"Đọc file: {file_path} ({total} URLs)")
        self.LogSignal.emit(f"=== GIAI ĐOẠN 1: Kiểm tra {total} video (local/online) ===")

        downloaded = []
        skipped_done = 0
        for i, url in enumerate(urls):
            if self._stop_event.is_set():
                self.LogSignal.emit("Đã yêu cầu dừng, không nhận thêm task mới.")
                break

            task_id = f"tap{cfg['start_index'] + i}"
            out_path = os.path.join(download_dir, f"{task_id}.mp4")

            # Task đã hoàn tất với đúng config hiện tại -> bỏ qua hẳn.
            if self._task_is_complete(task_id, out_path if os.path.exists(out_path) else None):
                self.LogSignal.emit(f"[{i+1}/{total}] Bỏ qua {task_id} (đã hoàn tất)")
                skipped_done += 1
                continue

            if os.path.exists(out_path):
                if not self.controller._video_ready(out_path):
                    self.LogSignal.emit(f"[{i+1}/{total}] {task_id}: file tải dở/hỏng -> tải lại")
                    try:
                        os.remove(out_path)
                    except OSError:
                        pass
                else:
                    self.LogSignal.emit(f"[{i+1}/{total}] Bỏ qua {task_id} (đã có trong download_dir)")
                    downloaded.append((task_id, out_path))
                    continue

            if os.path.exists(url):
                self.LogSignal.emit(f"[{i+1}/{total}] Copy local {task_id}: {url}")
                tmp_copy = out_path + ".part.mp4"
                try:
                    shutil.copy2(url, tmp_copy)
                    if not self.controller._video_ready(tmp_copy):
                        raise RuntimeError("video copy khong hop le")
                    os.replace(tmp_copy, out_path)
                    self.LogSignal.emit(f"[{i+1}/{total}] OK {task_id} (local)")
                    downloaded.append((task_id, out_path))
                except Exception as e:
                    self.LogSignal.emit(f"[{i+1}/{total}] LỖI copy {task_id}: {e}")
                    for path in (tmp_copy, out_path):
                        try:
                            os.remove(path)
                        except OSError:
                            pass
                continue

            self.LogSignal.emit(f"[{i+1}/{total}] Đang tải {task_id}...")
            ok = self.controller.DownloadVideo(url, out_path)
            if ok:
                self.LogSignal.emit(f"[{i+1}/{total}] OK {task_id}")
                downloaded.append((task_id, out_path))
            else:
                self.LogSignal.emit(f"[{i+1}/{total}] THẤT BẠI {task_id}")

        self.LogSignal.emit(f"\n=== GIAI ĐOẠN 2: Xử lý {len(downloaded)} video (song song={cfg['max_concurrent']}) ===")
        if skipped_done:
            self.LogSignal.emit(f"Đã bỏ qua {skipped_done} task hoàn tất từ lần chạy trước.")
        success = skipped_done
        completed = 0

        with ThreadPoolExecutor(max_workers=cfg['max_concurrent']) as executor:
            future_map = {}
            for task_id, local_path in downloaded:
                if self._stop_event.is_set():
                    break
                future = executor.submit(self.process_one_video, task_id, local_path)
                future_map[future] = task_id

            for future in as_completed(future_map):
                completed += 1
                if future.result():
                    success += 1
                self.ProgressSignal.emit(int(completed / max(len(downloaded), 1) * 100))

        self.FinishedSignal.emit(success, total)


# ============================================================
#  DIALOG XEM TRƯỚC VÙNG BLUR
# ============================================================
class BlurPreviewDialog(QDialog):
    """Cửa sổ riêng hiển thị preview vùng blur với tỷ lệ video thực tế"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Xem trước vùng làm mờ")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(300, 470)
        self.setStyleSheet(f"QDialog {{ background:{COLOR_BG}; }}")
        self._blur_start = 80
        self._blur_end = 95
        self._aspect = "16:9"
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        head = QLabel("📺  Xem trước vùng làm mờ")
        head.setStyleSheet(f"font-size:14px; font-weight:700; color:{COLOR_PRIMARY_DARK};")
        layout.addWidget(head)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background:{COLOR_CARD}; border:1px solid {COLOR_BORDER}; border-radius:10px; }}")
        card_lo = QVBoxLayout(card)
        card_lo.setContentsMargins(6, 6, 6, 6)
        self.preview = _BlurCanvas(self)
        card_lo.addWidget(self.preview, 1)
        layout.addWidget(card, 1)

        info = QHBoxLayout()
        self.lbl_start = QLabel("Bắt đầu: 80%")
        self.lbl_end = QLabel("Kết thúc: 95%")
        self.lbl_aspect = QLabel("Tỷ lệ: 16:9")
        for lbl in (self.lbl_start, self.lbl_end, self.lbl_aspect):
            lbl.setStyleSheet(
                f"background:{COLOR_CARD}; border:1px solid {COLOR_BORDER}; border-radius:6px; "
                f"padding:4px 8px; color:{COLOR_TEXT}; font-weight:600; font-size:11px;")
            info.addWidget(lbl)
        layout.addLayout(info)

    def update_preview(self, start, end, aspect="16:9", font_name="Arial", font_size=32, font_color="#FFD700"):
        self._blur_start = start
        self._blur_end = end
        self._aspect = aspect
        self.lbl_start.setText(f"Bắt đầu: {start}%")
        self.lbl_end.setText(f"Kết thúc: {end}%")
        self.lbl_aspect.setText(f"Tỷ lệ: {aspect}")
        self.preview.update_blur(start, end, aspect, font_name, font_size, font_color)
        self.preview.update()


class _BlurCanvas(QWidget):
    """Canvas vẽ preview bên trong dialog"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(280, 380)
        self._blur_start = 80
        self._blur_end = 95
        self._aspect = "16:9"
        self._font_name = "Arial"
        self._font_size = 32
        self._font_color = "#FFD700"

    def update_blur(self, start, end, aspect="16:9", font_name="Arial", font_size=32, font_color="#FFD700"):
        self._blur_start = start
        self._blur_end = end
        self._aspect = aspect
        self._font_name = font_name
        self._font_size = font_size
        self._font_color = font_color

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()
        margin = 20

        vw = w - 2 * margin
        vh = h - 2 * margin

        if self._aspect == "9:16":
            vw = min(vw, int(vh * 9 / 16))
            vh = int(vw * 16 / 9)
            if vh > h - 2 * margin:
                vh = h - 2 * margin
                vw = int(vh * 9 / 16)
        else:
            vh = min(vh, int(vw * 9 / 16))
            vw = int(vh * 16 / 9)
            if vw > w - 2 * margin:
                vw = w - 2 * margin
                vh = int(vw * 9 / 16)

        offset_x = (w - vw) // 2
        offset_y = (h - vh) // 2

        painter.fillRect(0, 0, w, h, QColor("#161B29"))

        painter.setPen(QPen(QColor("#4AD8C2"), 2))
        painter.drawRect(offset_x, offset_y, vw, vh)

        painter.fillRect(offset_x + 1, offset_y + 1, vw - 2, vh - 2, QColor(45, 50, 70, 200))

        blur_top = offset_y + int(vh * self._blur_start / 100)
        blur_h = int(vh * (self._blur_end - self._blur_start) / 100)

        painter.setPen(QPen(QColor("#FF9466"), 1))
        painter.setBrush(QBrush(QColor(255, 148, 102, 65)))
        painter.drawRect(offset_x, blur_top, vw, blur_h)

        painter.setPen(QPen(QColor(255, 148, 102, 40), 1))
        for i in range(0, vw + vh, 12):
            painter.drawLine(offset_x + i, blur_top, offset_x + i - vw, blur_top + vh)

        demo_text = "Phụ đề mới"
        preview_size = max(10, self._font_size)
        fn = self._font_name
        if fn.lower().endswith('.ttf'):
            fn = os.path.splitext(os.path.basename(fn))[0]
        sub_font = QFont(fn, preview_size, QFont.Weight.Bold)
        painter.setFont(sub_font)
        painter.setPen(QColor(self._font_color))
        text_rect = QRect(offset_x + 8, blur_top + (blur_h - preview_size - 4) // 2, vw - 16, preview_size + 8)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, demo_text)

        painter.setPen(QColor("#FF9466"))
        label_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(label_font)
        painter.drawText(offset_x + 6, blur_top - 6, f"▲ {self._blur_start}%")
        painter.drawText(offset_x + 6, blur_top + blur_h + 16, f"▼ {self._blur_end}%")

        arrow_x = offset_x + vw + 5
        painter.setPen(QPen(QColor("#FF9466"), 1))
        painter.drawLine(arrow_x, blur_top, arrow_x, blur_top + blur_h)
        painter.drawLine(arrow_x, blur_top, arrow_x + 4, blur_top + 4)
        painter.drawLine(arrow_x, blur_top + blur_h, arrow_x + 4, blur_top + blur_h - 4)

        painter.setPen(QColor("#4AD8C2"))
        header_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(header_font)
        painter.drawText(offset_x + 8, offset_y + 18, self._aspect)

        painter.setPen(QColor("#9AA3B2"))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(w // 2 - 32, offset_y + vh + 28, "khung video")


# ============================================================
#  DIALOG XEM TRƯỚC PNG OVERLAY
# ============================================================
class PngOverlayPreviewDialog(QDialog):
    """Cua so rieng hien thi preview PNG overlay voi ty le video thuc te"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Xem trước ảnh PNG")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(300, 470)
        self.setStyleSheet(f"QDialog {{ background:{COLOR_BG}; }}")
        self._pos_x = 50
        self._pos_y = 10
        self._width_percent = 40
        self._anchor = "center"
        self._aspect = "16:9"
        self._png_path = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        head = QLabel("🖼️  Xem trước ảnh PNG")
        head.setStyleSheet(f"font-size:14px; font-weight:700; color:{COLOR_PRIMARY_DARK};")
        layout.addWidget(head)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background:{COLOR_CARD}; border:1px solid {COLOR_BORDER}; border-radius:10px; }}")
        card_lo = QVBoxLayout(card)
        card_lo.setContentsMargins(6, 6, 6, 6)
        self.preview = _PngOverlayCanvas(self)
        card_lo.addWidget(self.preview, 1)
        layout.addWidget(card, 1)

        info = QHBoxLayout()
        self.lbl_pos = QLabel("Vị trí: 50%, 10%")
        self.lbl_size = QLabel("Kích thước: 40%")
        self.lbl_aspect = QLabel("Tỷ lệ: 16:9")
        for lbl in (self.lbl_pos, self.lbl_size, self.lbl_aspect):
            lbl.setStyleSheet(
                f"background:{COLOR_CARD}; border:1px solid {COLOR_BORDER}; border-radius:6px; "
                f"padding:4px 8px; color:{COLOR_TEXT}; font-weight:600; font-size:11px;")
            info.addWidget(lbl)
        layout.addLayout(info)

    def update_preview(self, pos_x, pos_y, width_percent, anchor="center", aspect="16:9", png_path=None):
        self._pos_x = pos_x
        self._pos_y = pos_y
        self._width_percent = width_percent
        self._anchor = anchor
        self._aspect = aspect
        self._png_path = png_path
        self.lbl_pos.setText(f"Vị trí: {pos_x}%, {pos_y}%")
        self.lbl_size.setText(f"Kích thước: {width_percent}%")
        self.lbl_aspect.setText(f"Tỷ lệ: {aspect}")
        self.preview.update_overlay(pos_x, pos_y, width_percent, anchor, aspect, png_path)
        self.preview.update()


class _PngOverlayCanvas(QWidget):
    """Canvas ve preview PNG overlay ben trong dialog"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(280, 380)
        self._pos_x = 50
        self._pos_y = 10
        self._width_percent = 40
        self._anchor = "center"
        self._aspect = "16:9"
        self._png_path = None
        self._pixmap = None

    def update_overlay(self, pos_x, pos_y, width_percent, anchor="center", aspect="16:9", png_path=None):
        self._pos_x = pos_x
        self._pos_y = pos_y
        self._width_percent = width_percent
        self._anchor = anchor
        self._aspect = aspect
        self._png_path = png_path
        if png_path and os.path.exists(png_path):
            self._pixmap = QPixmap(png_path)
        else:
            self._pixmap = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        margin = 20

        vw = w - 2 * margin
        vh = h - 2 * margin

        if self._aspect == "9:16":
            vw = min(vw, int(vh * 9 / 16))
            vh = int(vw * 16 / 9)
            if vh > h - 2 * margin:
                vh = h - 2 * margin
                vw = int(vh * 9 / 16)
        else:
            vh = min(vh, int(vw * 9 / 16))
            vw = int(vh * 16 / 9)
            if vw > w - 2 * margin:
                vw = w - 2 * margin
                vh = int(vw * 9 / 16)

        offset_x = (w - vw) // 2
        offset_y = (h - vh) // 2

        painter.fillRect(0, 0, w, h, QColor("#161B29"))

        painter.setPen(QPen(QColor("#4AD8C2"), 2))
        painter.drawRect(offset_x, offset_y, vw, vh)
        painter.fillRect(offset_x + 1, offset_y + 1, vw - 2, vh - 2, QColor(45, 50, 70, 200))

        # Ve PNG overlay neu co
        if self._pixmap and not self._pixmap.isNull():
            # Tinh kich thuoc PNG scaled
            png_w = int(vw * self._width_percent / 100)
            scaled = self._pixmap.scaledToWidth(png_w, Qt.TransformationMode.SmoothTransformation)
            pw = scaled.width()
            ph = scaled.height()

            # Tinh toa do
            if self._anchor == "top_left":
                px = offset_x + int((vw - pw) * self._pos_x / 100)
                py = offset_y + int((vh - ph) * self._pos_y / 100)
            else:
                # center
                px = offset_x + int((vw - pw) * self._pos_x / 100)
                py = offset_y + int((vh - ph) * self._pos_y / 100)

            painter.drawPixmap(px, py, scaled)

            # Ve khung quanh PNG
            painter.setPen(QPen(QColor("#FFD700"), 1, Qt.PenStyle.DashLine))
            painter.drawRect(px, py, pw, ph)

        painter.setPen(QColor("#4AD8C2"))
        header_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(header_font)
        painter.drawText(offset_x + 8, offset_y + 18, self._aspect)

        painter.setPen(QColor("#9AA3B2"))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(w // 2 - 32, offset_y + vh + 28, "khung video")


# ============================================================
#  CỬA SỔ CHÍNH
# ============================================================
class AutomationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = MainController()
        self.worker = None
        self.saved_config = load_saved_config()
        self.custom_font_path = None
        self._font_color = QColor("#FFFF00")
        self._outline_color = QColor("#000000")
        self._back_color = QColor("#80000000")

        self.setWindowTitle("MMO SubVideo AI - Tự Động Hóa")
        self.resize(1180, 980)
        self.setMinimumSize(980, 820)
        self.setStyleSheet(APP_STYLESHEET)

        self.InitUI()
        self.RestoreConfig()

    # ---------------------------------------------------
    def ScanDir(self, Path, Extension):
        if not os.path.exists(Path):
            return []
        if Extension == "dir":
            return [d for d in os.listdir(Path)
                    if os.path.isdir(os.path.join(Path, d))
                    and any(f.endswith(".pth") for f in os.listdir(os.path.join(Path, d)))]
        else:
            return [f for f in os.listdir(Path) if f.lower().endswith(Extension)]

    def OnBgmToggled(self, Checked):
        self.BgmCombo.setEnabled(Checked)
        if Checked:
            self.RadioMute.setChecked(True)
            self.RadioDuck.setEnabled(False)
        else:
            self.RadioDuck.setEnabled(True)

    def _update_color_btn(self, btn, color):
        btn.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;")

    def _pick_font_color(self):
        color = QColorDialog.getColor(self._font_color, self, "Chọn màu chữ")
        if color.isValid():
            self._font_color = color
            self._update_color_btn(self.FontColorBtn, color)
            if hasattr(self, 'BlurPreview') and self.BlurPreview.isVisible():
                self._on_blur_changed()

    def _pick_outline_color(self):
        color = QColorDialog.getColor(self._outline_color, self, "Chọn màu viền")
        if color.isValid():
            self._outline_color = color
            self._update_color_btn(self.OutlineColorBtn, color)

    def _pick_back_color(self):
        color = QColorDialog.getColor(self._back_color, self, "Chọn màu nền sub")
        if color.isValid():
            self._back_color = color
            self._update_color_btn(self.BackColorBtn, color)

    def _get_font_data_for_preview(self):
        fn = self.FontCombo.currentText()
        if self.custom_font_path:
            fn = self.custom_font_path
        fs = self.FontSizeSpin.value()
        fc = self._font_color.name()
        return fn, fs, fc

    def _on_blur_changed(self):
        start_val = self.BlurStartSlider.value()
        end_val = self.BlurEndSlider.value()
        if start_val >= end_val:
            if self.sender() == self.BlurStartSlider:
                self.BlurStartSlider.setValue(end_val - 1)
                return
            else:
                self.BlurEndSlider.setValue(start_val + 1)
                return
        self.BlurStartLabel.setText(f"{start_val}%")
        self.BlurEndLabel.setText(f"{end_val}%")
        aspect = self.AspectRatioCombo.currentText()
        if hasattr(self, 'BlurPreview') and self.BlurPreview.isVisible():
            fn, fs, fc = self._get_font_data_for_preview()
            self.BlurPreview.update_preview(start_val, end_val, aspect, fn, fs, fc)

    def _show_blur_preview(self):
        if not hasattr(self, 'BlurPreview'):
            self.BlurPreview = BlurPreviewDialog(self)
        if self.BlurPreview.isVisible():
            self.BlurPreview.hide()
            self.BtnBlurPreview.setStyleSheet(_push_btn_style(COLOR_PRIMARY))
        else:
            start_val = self.BlurStartSlider.value()
            end_val = self.BlurEndSlider.value()
            aspect = self.AspectRatioCombo.currentText()
            fn, fs, fc = self._get_font_data_for_preview()
            self.BlurPreview.update_preview(start_val, end_val, aspect, fn, fs, fc)
            main_pos = self.pos()
            main_size = self.size()
            dialog_x = main_pos.x() + main_size.width() + 10
            dialog_y = main_pos.y()
            self.BlurPreview.move(dialog_x, dialog_y)
            self.BlurPreview.show()
            self.BtnBlurPreview.setStyleSheet(_push_btn_style(COLOR_DANGER))

    def BrowseFont(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Chọn Font Chữ")
        dialog.resize(420, 320)
        dialog.setStyleSheet(f"QDialog {{ background:{COLOR_BG}; }}")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(_section_label("FONT HỆ THỐNG"))
        system_fonts = get_system_fonts()
        font_combo = QComboBox()
        font_combo.addItems(system_fonts)
        current = self.FontCombo.currentText()
        idx = font_combo.findText(current)
        if idx >= 0:
            font_combo.setCurrentIndex(idx)
        layout.addWidget(font_combo)

        layout.addWidget(_section_label("HOẶC FILE .TTF BÊN NGOÀI"))
        btn_browse = QPushButton("📁  Chọn file font...")
        btn_browse.setStyleSheet(_push_btn_style(COLOR_ACCENT))
        ext_font_path = [None]

        def browse_external():
            path, _ = QFileDialog.getOpenFileName(
                dialog, "Chọn file font", "", "TrueType Font (*.ttf);;All files (*)")
            if path:
                ext_font_path[0] = path
                font_name = os.path.splitext(os.path.basename(path))[0]
                font_combo.setCurrentText(font_name)
                QMessageBox.information(dialog, "Đã chọn", f"Font: {font_name}\n{path}")

        btn_browse.clicked.connect(browse_external)
        layout.addWidget(btn_browse)
        layout.addStretch()

        btn_ok = QPushButton("Áp dụng")
        btn_ok.setStyleSheet(_push_btn_style(COLOR_PRIMARY))

        def apply_font():
            if ext_font_path[0]:
                self.FontCombo.setCurrentText(os.path.splitext(os.path.basename(ext_font_path[0]))[0])
                self.custom_font_path = ext_font_path[0]
            else:
                self.FontCombo.setCurrentText(font_combo.currentText())
                self.custom_font_path = None
            dialog.accept()

        btn_ok.clicked.connect(apply_font)
        layout.addWidget(btn_ok)
        dialog.exec()

    # ---------------------------------------------------
    #  XÂY DỰNG GIAO DIỆN
    # ---------------------------------------------------
    def InitUI(self):
        mw = QWidget()
        self.setCentralWidget(mw)
        root = QVBoxLayout(mw)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        # ===== HÀNG TRÊN: FILE + CẤU HÌNH CHẠY (luôn hiển thị) =====
        top_card, top_body = _make_card("Nguồn dữ liệu & Cấu hình chạy", "📂", show_title=False)
        top_lo = QHBoxLayout()
        top_lo.setSpacing(20)
        top_body.addLayout(top_lo)

        file_box = QVBoxLayout()
        file_box.setSpacing(8)
        file_box.addWidget(_section_label("DANH SÁCH LINK / VIDEO (.txt)"))
        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        self.FilePathInput = QLineEdit()
        self.FilePathInput.setPlaceholderText("Chọn file .txt chứa danh sách link hoặc đường dẫn video...")
        bb = QPushButton("Chọn file")
        bb.setStyleSheet(_push_btn_style(COLOR_ACCENT))
        bb.clicked.connect(self.BrowseFile)
        file_row.addWidget(self.FilePathInput, 1)
        file_row.addWidget(bb)
        file_box.addLayout(file_row)
        top_lo.addLayout(file_box, 2)

        sep = QFrame()
        sep.setObjectName("VSep")
        sep.setFrameShape(QFrame.Shape.VLine)
        top_lo.addWidget(sep)

        run_box = QVBoxLayout()
        run_box.setSpacing(8)
        run_box.addWidget(_section_label("THAM SỐ CHẠY"))
        run_row = QHBoxLayout()
        run_row.setSpacing(8)
        run_row.addWidget(QLabel("Bắt đầu từ:"))
        self.StartIndexSpin = QSpinBox()
        self.StartIndexSpin.setRange(1, 999999)
        self.StartIndexSpin.setValue(1)
        run_row.addWidget(self.StartIndexSpin)
        run_row.addSpacing(10)
        run_row.addWidget(QLabel("Song song:"))
        self.ParallelSpin = QSpinBox()
        self.ParallelSpin.setRange(1, 10)
        self.ParallelSpin.setValue(2)
        run_row.addWidget(self.ParallelSpin)
        run_box.addLayout(run_row)
        top_lo.addLayout(run_box, 1)

        root.addWidget(top_card)

        # ===== TABS NỘI DUNG CHI TIẾT =====
        tabs = QTabWidget()
        tabs.addTab(_wrap_scroll(self._build_voice_tab()), "🎙  Giọng nói && Âm thanh")
        tabs.addTab(_wrap_scroll(self._build_video_tab()), "🌐  Dịch thuật && Phụ đề")
        tabs.addTab(_wrap_scroll(self._build_process_tab()), "⚙️  Xử lý video && Phần cứng")
        root.addWidget(tabs, 5)

        # ===== NÚT CẤU HÌNH =====
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.BtnSaveConfig = QPushButton("💾  Lưu cấu hình")
        self.BtnSaveConfig.setStyleSheet(_push_btn_style(COLOR_PRIMARY))
        self.BtnSaveConfig.clicked.connect(self.SaveCurrentConfig)
        btn_row.addWidget(self.BtnSaveConfig)

        self.BtnLoadConfig = QPushButton("↺  Đặt lại")
        self.BtnLoadConfig.setStyleSheet(_push_btn_style("#9AA3B2"))
        self.BtnLoadConfig.clicked.connect(self.ResetConfig)
        btn_row.addWidget(self.BtnLoadConfig)

        self.BtnExportConfig = QPushButton("⭳  Xuất config")
        self.BtnExportConfig.setStyleSheet(_push_btn_style(COLOR_SUCCESS))
        self.BtnExportConfig.clicked.connect(self.ExportConfig)
        btn_row.addWidget(self.BtnExportConfig)

        self.BtnImportConfig = QPushButton("⭱  Nhập config")
        self.BtnImportConfig.setStyleSheet(_push_btn_style("#8B5CF6"))
        self.BtnImportConfig.clicked.connect(self.ImportConfig)
        btn_row.addWidget(self.BtnImportConfig)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # ===== NÚT BẮT ĐẦU =====
        self.BtnStart = QPushButton("▶   BẮT ĐẦU CHẠY HÀNG LOẠT")
        self.BtnStart.setMinimumHeight(48)
        self.BtnStart.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, "
            f"stop:0 {COLOR_WARN}, stop:1 #EA580C); color:white; font-weight:700; "
            f"font-size:15px; border:none; border-radius:10px; }}"
            f"QPushButton:hover {{ background:#EA580C; }}"
            f"QPushButton:disabled {{ background:#C9CDD6; color:#F2F2F2; }}")
        self.BtnStart.clicked.connect(self.StartAutomation)
        root.addWidget(self.BtnStart)

        # ===== PROGRESS =====
        self.Progress = QProgressBar()
        self.Progress.setFormat("%p%  •  %v/%m video")
        root.addWidget(self.Progress)

        # ===== LOG =====
        log_head = QHBoxLayout()
        lgl = QLabel("🧾  Nhật ký tiến trình")
        lgl.setStyleSheet(f"font-weight:700; color:{COLOR_PRIMARY_DARK};")
        log_head.addWidget(lgl)
        log_head.addStretch()
        root.addLayout(log_head)

        self.LogArea = QTextEdit()
        self.LogArea.setObjectName("LogArea")
        self.LogArea.setReadOnly(True)
        self.LogArea.setMinimumHeight(110)
        self.LogArea.setMaximumHeight(130)
        root.addWidget(self.LogArea)

    # ---------------------------------------------------
    #  TAB 1: GIỌNG NÓI & ÂM THANH
    # ---------------------------------------------------
    def _build_voice_tab(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(6, 14, 6, 6)
        outer.setSpacing(14)
        cols = QHBoxLayout()
        cols.setSpacing(18)

        # ---- Giọng nói ----
        vg, vl = _make_card("Giọng nói", "🗣")
        vl.setSpacing(12)

        vl.addWidget(_section_label("NGUỒN GIỌNG NÓI"))
        rr = QHBoxLayout()
        rr.setSpacing(10)
        self.RadioGtts = QRadioButton("GTTS")
        self.RadioEdge = QRadioButton("Edge")
        self.RadioTikTok = QRadioButton("TikTok")
        self.RadioVietNeu = QRadioButton("VN Cloud")
        self.RadioRvc = QRadioButton("RVC")
        self.RadioEdge.setChecked(True)
        for r in (self.RadioGtts, self.RadioEdge, self.RadioTikTok, self.RadioVietNeu, self.RadioRvc):
            rr.addWidget(r)
        vl.addLayout(rr)

        tiktok_layout = QHBoxLayout()
        tiktok_layout.setSpacing(8)
        tiktok_layout.addWidget(QLabel("TikTok Voice:"))
        self.TikTokVoiceCombo = QComboBox()
        self.TikTokVoiceCombo.addItems(["cutefemale", "confidentmale"])
        self.TikTokVoiceCombo.setCurrentText("cutefemale")
        self.TikTokVoiceCombo.setEnabled(False)
        tiktok_layout.addWidget(self.TikTokVoiceCombo)
        tiktok_layout.addStretch()
        vl.addLayout(tiktok_layout)

        vc1 = QHBoxLayout()
        vc1.setSpacing(8)
        vc1.addWidget(QLabel("Edge:"))
        self.EdgeVoiceCombo = QComboBox()
        self.EdgeVoiceCombo.addItems(["vi-VN-HoaiMyNeural (Nữ)", "vi-VN-NamMinhNeural (Nam)"])
        vc1.addWidget(self.EdgeVoiceCombo, 1)
        vl.addLayout(vc1)

        vc2 = QHBoxLayout()
        vc2.setSpacing(8)
        vc2.addWidget(QLabel("GCloud:"))
        self.NeutralVoiceCombo = QComboBox()
        self.NeutralVoiceCombo.addItems(["vi-VN-Wavenet-C (Nam)", "vi-VN-Wavenet-A (Nữ)", "vi-VN-Neural2-A (Nữ)", "vi-VN-Neural2-B (Nam)"])
        vc2.addWidget(self.NeutralVoiceCombo, 1)
        vl.addLayout(vc2)

        vl.addWidget(_section_label("RVC (VOICE CLONE)"))
        rv1 = QHBoxLayout()
        rv1.setSpacing(8)
        rv1.addWidget(QLabel("Engine:"))
        self.RvcBaseCombo = QComboBox()
        self.RvcBaseCombo.addItems(["Edge TTS", "Google TTS Free", "Google Cloud Token"])
        self.RvcBaseCombo.setEnabled(False)
        rv1.addWidget(self.RvcBaseCombo, 1)
        rv1.addSpacing(6)
        rv1.addWidget(QLabel("Model:"))
        self.ModelCombo = QComboBox()
        self.ModelCombo.addItems(self.ScanDir("rvc", "dir"))
        self.ModelCombo.setEnabled(False)
        rv1.addWidget(self.ModelCombo, 1)
        vl.addLayout(rv1)

        rv2 = QHBoxLayout()
        rv2.setSpacing(8)
        rv2.addWidget(QLabel("Mode:"))
        self.RvcModeCombo = QComboBox()
        self.RvcModeCombo.addItems(["docker", "native"])
        self.RvcModeCombo.setEnabled(False)
        rv2.addWidget(self.RvcModeCombo, 1)
        rv2.addSpacing(6)
        rv2.addWidget(QLabel("F0 Key:"))
        self.F0Spin = QSpinBox()
        self.F0Spin.setRange(-24, 24)
        self.F0Spin.setValue(8)
        rv2.addWidget(self.F0Spin, 1)
        vl.addLayout(rv2)

        def update_voice_ui():
            ir = self.RadioRvc.isChecked()
            self.RvcBaseCombo.setEnabled(ir)
            self.ModelCombo.setEnabled(ir)
            self.RvcModeCombo.setEnabled(ir)
            self.TikTokVoiceCombo.setEnabled(self.RadioTikTok.isChecked())
            if ir:
                self.F0Spin.setValue(4)
            elif self.RadioGtts.isChecked():
                self.F0Spin.setValue(8)
            else:
                self.F0Spin.setValue(0)

        self.RadioGtts.toggled.connect(update_voice_ui)
        self.RadioEdge.toggled.connect(update_voice_ui)
        self.RadioTikTok.toggled.connect(update_voice_ui)
        self.RadioVietNeu.toggled.connect(update_voice_ui)
        self.RadioRvc.toggled.connect(update_voice_ui)

        vl.addWidget(_section_label("TỐC ĐỘ ĐỌC"))
        r0 = QHBoxLayout()
        r0.setSpacing(8)
        r0.addWidget(QLabel("EdgeRate:"))
        self.EdgeRateInput = QLineEdit("+25%")
        self.EdgeRateInput.setFixedWidth(70)
        r0.addWidget(self.EdgeRateInput)
        r0.addStretch()
        vl.addLayout(r0)

        r1 = QHBoxLayout()
        r1.setSpacing(8)
        r1.addWidget(QLabel("Voice:"))
        self.VoiceRateSlider = QSlider(Qt.Orientation.Horizontal)
        self.VoiceRateSlider.setRange(5, 30)
        self.VoiceRateSlider.setValue(16)
        self.VoiceRateLabel = QLabel("1.6")
        self.VoiceRateLabel.setFixedWidth(30)
        self.VoiceRateSlider.valueChanged.connect(lambda v: self.VoiceRateLabel.setText(f"{v/10.0}"))
        r1.addWidget(self.VoiceRateSlider, 1)
        r1.addWidget(self.VoiceRateLabel)
        vl.addLayout(r1)

        r2 = QHBoxLayout()
        r2.setSpacing(8)
        r2.addWidget(QLabel("GTTS:"))
        self.GttsRateSlider = QSlider(Qt.Orientation.Horizontal)
        self.GttsRateSlider.setRange(5, 30)
        self.GttsRateSlider.setValue(19)
        self.GttsRateLabel = QLabel("1.9")
        self.GttsRateLabel.setFixedWidth(30)
        self.GttsRateSlider.valueChanged.connect(lambda v: self.GttsRateLabel.setText(f"{v/10.0}"))
        r2.addWidget(self.GttsRateSlider, 1)
        r2.addWidget(self.GttsRateLabel)
        vl.addLayout(r2)

        r3 = QHBoxLayout()
        r3.setSpacing(8)
        r3.addWidget(QLabel("Cloud:"))
        self.DVoiceRateSlider = QSlider(Qt.Orientation.Horizontal)
        self.DVoiceRateSlider.setRange(5, 30)
        self.DVoiceRateSlider.setValue(10)
        self.DVoiceRateLabel = QLabel("1.0")
        self.DVoiceRateLabel.setFixedWidth(30)
        self.DVoiceRateSlider.valueChanged.connect(lambda v: self.DVoiceRateLabel.setText(f"{v/10.0}"))
        r3.addWidget(self.DVoiceRateSlider, 1)
        r3.addWidget(self.DVoiceRateLabel)
        vl.addLayout(r3)

        cols.addWidget(vg, 3)

        # ---- Âm thanh ----
        ag, al = _make_card("Âm thanh gốc & Nhạc nền", "🔊")
        al.setSpacing(12)
        al.addWidget(_section_label("XỬ LÝ ÂM GỐC"))
        arow = QHBoxLayout()
        arow.setSpacing(10)
        self.RadioMute = QRadioButton("Tắt tiếng")
        self.RadioDuck = QRadioButton("Giảm âm")
        self.RadioDuck.setChecked(True)
        arow.addWidget(self.RadioMute)
        arow.addWidget(self.RadioDuck)
        arow.addStretch()
        al.addLayout(arow)

        al.addWidget(_section_label("NHẠC NỀN (BGM)"))
        brow = QHBoxLayout()
        brow.setSpacing(8)
        self.BgmCheck = QCheckBox("Bật nhạc nền")
        brow.addWidget(self.BgmCheck)
        brow.addStretch()
        al.addLayout(brow)
        self.BgmCombo = QComboBox()
        self.BgmCombo.addItems(self.ScanDir("bgm", (".mp3", ".wav", ".m4a")))
        self.BgmCombo.setEnabled(False)
        self.BgmCheck.toggled.connect(self.OnBgmToggled)
        al.addWidget(self.BgmCombo)
        al.addStretch()

        cols.addWidget(ag, 2)
        outer.addLayout(cols)
        outer.addStretch()
        return page

    # ---------------------------------------------------
    #  TAB 2: DỊCH THUẬT & PHỤ ĐỀ
    # ---------------------------------------------------
    def _build_video_tab(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(6, 14, 6, 6)
        outer.setSpacing(14)

        # ---- Dịch thuật ----
        tg, tl = _make_card("Dịch thuật", "🌐")
        tl.setSpacing(12)

        tr0 = QHBoxLayout()
        tr0.setSpacing(14)
        self.RadioFilter = QRadioButton("Bộ lọc")
        self.RadioGemini = QRadioButton("Gemini AI")
        self.RadioFilter.setChecked(True)
        tr0.addWidget(self.RadioFilter)
        tr0.addWidget(self.RadioGemini)
        tr0.addStretch()
        tl.addLayout(tr0)

        tr1 = QHBoxLayout()
        tr1.setSpacing(8)
        tr1.addWidget(QLabel("Kiểu dịch:"))
        self.StyleCombo = QComboBox()
        self.StyleCombo.addItems(["tinh_cam", "hai_huoc", "giang_ho", "xa_giao"])
        self.RadioGemini.toggled.connect(lambda c: self.StyleCombo.setEnabled(not c))
        tr1.addWidget(self.StyleCombo, 1)
        tr1.addSpacing(10)
        tr1.addWidget(QLabel("Ngôn ngữ nguồn:"))
        self.LangCombo = QComboBox()
        self.LangCombo.addItems(["zh", "en", "ja", "ko", "vi"])
        tr1.addWidget(self.LangCombo, 1)
        tl.addLayout(tr1)

        tr2 = QHBoxLayout()
        tr2.setSpacing(8)
        tr2.addWidget(QLabel("Model STT:"))
        self.SttModelCombo = QComboBox()
        self.SttModelCombo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.SttModelCombo.setCurrentText("small")
        tr2.addWidget(self.SttModelCombo, 1)
        tr2.addStretch(1)
        tl.addLayout(tr2)

        outer.addWidget(tg)

        # ---- Video & Phụ đề ----
        vg2, vl2 = _make_card("Video & Phụ đề", "🎞")
        vl2.setSpacing(14)

        vl2.addWidget(_section_label("HIỂN THỊ CHUNG"))
        vr1 = QHBoxLayout()
        vr1.setSpacing(10)
        self.BlurCheck = QCheckBox("Làm mờ phụ đề cũ")
        self.BlurCheck.setChecked(True)
        vr1.addWidget(self.BlurCheck)
        vr1.addStretch()
        vl2.addLayout(vr1)

        vr1b = QHBoxLayout()
        vr1b.setSpacing(8)
        vr1b.addWidget(QLabel("Tỷ lệ khung hình:"))
        self.AspectRatioCombo = QComboBox()
        self.AspectRatioCombo.addItems(["auto", "16:9", "9:16"])
        self.AspectRatioCombo.setCurrentText("auto")
        vr1b.addWidget(self.AspectRatioCombo)
        self.AspectRatioCombo.currentTextChanged.connect(
            lambda _: self._on_blur_changed() if hasattr(self, 'BlurPreview') else None)
        self.AspectRatioCombo.currentTextChanged.connect(
            lambda _: self._update_png_preview() if hasattr(self, 'PngPreview') else None)
        vr1b.addSpacing(16)
        vr1b.addWidget(QLabel("Cỡ chữ phụ đề:"))
        self.FontSizeSpin = QSpinBox()
        self.FontSizeSpin.setRange(16, 60)
        self.FontSizeSpin.setValue(32)
        self.FontSizeSpin.valueChanged.connect(
            lambda _: self._on_blur_changed() if hasattr(self, 'BlurPreview') and self.BlurPreview.isVisible() else None)
        vr1b.addWidget(self.FontSizeSpin)
        vr1b.addStretch()
        vl2.addLayout(vr1b)

        vr2 = QHBoxLayout()
        vr2.setSpacing(8)
        vr2.addWidget(QLabel("Vị trí phụ đề:"))
        self.SubPosLabel = QLabel("Tự động (theo vùng blur)")
        self.SubPosLabel.setStyleSheet(f"color:{COLOR_MUTED}; font-style:italic;")
        vr2.addWidget(self.SubPosLabel)
        vr2.addStretch()
        vl2.addLayout(vr2)

        sep1 = QFrame()
        sep1.setObjectName("CardSep")
        sep1.setFrameShape(QFrame.Shape.HLine)
        vl2.addWidget(sep1)

        vl2.addWidget(_section_label("VÙNG LÀM MỜ"))
        blur_row = QHBoxLayout()
        blur_row.setSpacing(18)
        self.BtnBlurPreview = QPushButton("📺\nXem trước")
        self.BtnBlurPreview.setFixedSize(92, 58)
        self.BtnBlurPreview.setStyleSheet(_push_btn_style(COLOR_PRIMARY, radius=8, pad="4px"))
        self.BtnBlurPreview.clicked.connect(self._show_blur_preview)
        blur_row.addWidget(self.BtnBlurPreview)

        bc = QVBoxLayout()
        bc.setSpacing(12)
        b1 = QHBoxLayout()
        b1.setSpacing(8)
        b1.addWidget(QLabel("Bắt đầu:"))
        self.BlurStartSlider = QSlider(Qt.Orientation.Horizontal)
        self.BlurStartSlider.setRange(50, 95)
        self.BlurStartSlider.setValue(80)
        self.BlurStartLabel = QLabel("80%")
        self.BlurStartLabel.setFixedWidth(40)
        self.BlurStartSlider.valueChanged.connect(self._on_blur_changed)
        b1.addWidget(self.BlurStartSlider, 1)
        b1.addWidget(self.BlurStartLabel)
        bc.addLayout(b1)

        b2 = QHBoxLayout()
        b2.setSpacing(8)
        b2.addWidget(QLabel("Kết thúc:"))
        self.BlurEndSlider = QSlider(Qt.Orientation.Horizontal)
        self.BlurEndSlider.setRange(55, 100)
        self.BlurEndSlider.setValue(95)
        self.BlurEndLabel = QLabel("95%")
        self.BlurEndLabel.setFixedWidth(40)
        self.BlurEndSlider.valueChanged.connect(self._on_blur_changed)
        b2.addWidget(self.BlurEndSlider, 1)
        b2.addWidget(self.BlurEndLabel)
        bc.addLayout(b2)

        b3 = QHBoxLayout()
        b3.setSpacing(8)
        b3.addWidget(QLabel("Cường độ:"))
        self.BlurIntensitySlider = QSlider(Qt.Orientation.Horizontal)
        self.BlurIntensitySlider.setRange(1, 15)
        self.BlurIntensitySlider.setValue(10)
        self.BlurIntensityLabel = QLabel("10")
        self.BlurIntensityLabel.setFixedWidth(40)
        self.BlurIntensitySlider.valueChanged.connect(lambda v: self.BlurIntensityLabel.setText(str(v)))
        b3.addWidget(self.BlurIntensitySlider, 1)
        b3.addWidget(self.BlurIntensityLabel)
        bc.addLayout(b3)

        blur_row.addLayout(bc, 1)
        vl2.addLayout(blur_row)

        sep2 = QFrame()
        sep2.setObjectName("CardSep")
        sep2.setFrameShape(QFrame.Shape.HLine)
        vl2.addWidget(sep2)

        vl2.addWidget(_section_label("FONT CHỮ & MÀU SẮC"))
        vr4 = QHBoxLayout()
        vr4.setSpacing(8)
        vr4.addWidget(QLabel("Font:"))
        self.FontCombo = QComboBox()
        system_fonts = get_system_fonts()
        preferred = ["Arial", "Times New Roman", "Tahoma", "Verdana", "Calibri",
                      "Roboto", "Noto Sans", "Open Sans", "DejaVu Sans", "Ubuntu"]
        available = [f for f in preferred if f in system_fonts]
        if not available:
            available = system_fonts[:20]
        self.FontCombo.addItems(available)
        if "Arial" in available:
            self.FontCombo.setCurrentText("Arial")
        vr4.addWidget(self.FontCombo, 1)
        self.BtnBrowseFont = QPushButton("Chọn font...")
        self.BtnBrowseFont.setStyleSheet(_push_btn_style(COLOR_ACCENT))
        self.BtnBrowseFont.clicked.connect(self.BrowseFont)
        self.FontCombo.currentTextChanged.connect(lambda _: self._on_blur_changed()
            if hasattr(self, 'BlurPreview') and self.BlurPreview.isVisible() else None)
        vr4.addWidget(self.BtnBrowseFont)
        vl2.addLayout(vr4)

        vr5 = QHBoxLayout()
        vr5.setSpacing(10)
        vr5.addWidget(QLabel("Màu chữ:"))
        self.FontColorBtn = QPushButton()
        self.FontColorBtn.setFixedSize(48, 28)
        self._update_color_btn(self.FontColorBtn, self._font_color)
        self.FontColorBtn.clicked.connect(self._pick_font_color)
        vr5.addWidget(self.FontColorBtn)

        vr5.addSpacing(18)
        vr5.addWidget(QLabel("Viền:"))
        self.OutlineColorBtn = QPushButton()
        self.OutlineColorBtn.setFixedSize(48, 28)
        self._update_color_btn(self.OutlineColorBtn, self._outline_color)
        self.OutlineColorBtn.clicked.connect(self._pick_outline_color)
        vr5.addWidget(self.OutlineColorBtn)

        vr5.addSpacing(18)
        vr5.addWidget(QLabel("Nền phụ đề:"))
        self.SubBgCheck = QCheckBox("Bật")
        self.SubBgCheck.setChecked(True)
        vr5.addWidget(self.SubBgCheck)
        self.BackColorBtn = QPushButton()
        self.BackColorBtn.setFixedSize(48, 28)
        self._update_color_btn(self.BackColorBtn, self._back_color)
        self.BackColorBtn.clicked.connect(self._pick_back_color)
        vr5.addWidget(self.BackColorBtn)
        vr5.addStretch()
        vl2.addLayout(vr5)

        # ---- Thêm tab PNG Overlay và HasSubtitle vào cuối ----
        sep3 = QFrame()
        sep3.setObjectName("CardSep")
        sep3.setFrameShape(QFrame.Shape.HLine)
        vl2.addWidget(sep3)

        vl2.addWidget(_section_label("CHÈN ẢNH PNG OVERLAY"))
        png_row1 = QHBoxLayout()
        png_row1.setSpacing(8)
        self.PngOverlayCheck = QCheckBox("Bật chèn ảnh PNG")
        self.PngOverlayCheck.setChecked(False)
        png_row1.addWidget(self.PngOverlayCheck)
        self.PngFullVideoCheck = QCheckBox("Kéo dài toàn bộ video")
        self.PngFullVideoCheck.setChecked(False)
        png_row1.addWidget(self.PngFullVideoCheck)
        png_row1.addStretch()
        vl2.addLayout(png_row1)

        png_file_row = QHBoxLayout()
        png_file_row.setSpacing(8)
        self.PngPathEdit = QLineEdit()
        self.PngPathEdit.setPlaceholderText("Chọn file PNG...")
        self.PngPathEdit.setReadOnly(True)
        self.BtnBrowsePng = QPushButton("📁  Chọn PNG")
        self.BtnBrowsePng.setStyleSheet(_push_btn_style(COLOR_ACCENT))
        self.BtnBrowsePng.clicked.connect(self._browse_png)
        png_file_row.addWidget(self.PngPathEdit, 1)
        png_file_row.addWidget(self.BtnBrowsePng)
        vl2.addLayout(png_file_row)

        # Sliders cho vi tri, kich thuoc
        png_pos_row = QHBoxLayout()
        png_pos_row.setSpacing(8)
        png_pos_row.addWidget(QLabel("Vị trí X%:"))
        self.PngPosXSlider = QSlider(Qt.Orientation.Horizontal)
        self.PngPosXSlider.setRange(0, 100)
        self.PngPosXSlider.setValue(50)
        self.PngPosXLabel = QLabel("50%")
        self.PngPosXLabel.setFixedWidth(34)
        self.PngPosXSlider.valueChanged.connect(lambda v: self._on_png_slider_changed(v, "pos_x"))
        png_pos_row.addWidget(self.PngPosXSlider, 1)
        png_pos_row.addWidget(self.PngPosXLabel)
        vl2.addLayout(png_pos_row)

        png_pos_row2 = QHBoxLayout()
        png_pos_row2.setSpacing(8)
        png_pos_row2.addWidget(QLabel("Vị trí Y%:"))
        self.PngPosYSlider = QSlider(Qt.Orientation.Horizontal)
        self.PngPosYSlider.setRange(0, 100)
        self.PngPosYSlider.setValue(10)
        self.PngPosYLabel = QLabel("10%")
        self.PngPosYLabel.setFixedWidth(34)
        self.PngPosYSlider.valueChanged.connect(lambda v: self._on_png_slider_changed(v, "pos_y"))
        png_pos_row2.addWidget(self.PngPosYSlider, 1)
        png_pos_row2.addWidget(self.PngPosYLabel)
        vl2.addLayout(png_pos_row2)

        png_size_row = QHBoxLayout()
        png_size_row.setSpacing(8)
        png_size_row.addWidget(QLabel("Rộng%:"))
        self.PngWidthSlider = QSlider(Qt.Orientation.Horizontal)
        self.PngWidthSlider.setRange(5, 500)
        self.PngWidthSlider.setValue(40)
        self.PngWidthLabel = QLabel("40%")
        self.PngWidthLabel.setFixedWidth(34)
        self.PngWidthSlider.valueChanged.connect(lambda v: self._on_png_slider_changed(v, "width"))
        png_size_row.addWidget(self.PngWidthSlider, 1)
        png_size_row.addWidget(self.PngWidthLabel)
        vl2.addLayout(png_size_row)

        # Start/End time
        png_time_row = QHBoxLayout()
        png_time_row.setSpacing(8)
        png_time_row.addWidget(QLabel("Bắt đầu (s):"))
        self.PngStartTimeSpin = QSpinBox()
        self.PngStartTimeSpin.setRange(0, 9999)
        self.PngStartTimeSpin.setValue(0)
        self.PngStartTimeSpin.setSuffix(" s")
        png_time_row.addWidget(self.PngStartTimeSpin)
        self.PngStartTimeSpin.valueChanged.connect(lambda _: self._update_png_preview())
        png_time_row.addSpacing(6)
        png_time_row.addWidget(QLabel("Kết thúc (s):"))
        self.PngEndTimeSpin = QSpinBox()
        self.PngEndTimeSpin.setRange(0, 9999)
        self.PngEndTimeSpin.setValue(0)
        self.PngEndTimeSpin.setSuffix(" s")
        png_time_row.addWidget(self.PngEndTimeSpin)
        self.PngEndTimeSpin.valueChanged.connect(lambda _: self._update_png_preview())
        png_time_row.addStretch()
        vl2.addLayout(png_time_row)

        # Anchor + Preview button
        png_bottom_row = QHBoxLayout()
        png_bottom_row.setSpacing(8)
        png_bottom_row.addWidget(QLabel("Anchor:"))
        self.PngAnchorCombo = QComboBox()
        self.PngAnchorCombo.addItems(["center", "top_left"])
        self.PngAnchorCombo.setCurrentText("center")
        png_bottom_row.addWidget(self.PngAnchorCombo)
        self.PngAnchorCombo.currentTextChanged.connect(lambda _: self._update_png_preview())
        png_bottom_row.addSpacing(16)
        self.BtnPngPreview = QPushButton("👁️  Xem trước")
        self.BtnPngPreview.setStyleSheet(_push_btn_style(COLOR_PRIMARY))
        self.BtnPngPreview.clicked.connect(self._show_png_preview)
        png_bottom_row.addWidget(self.BtnPngPreview)
        png_bottom_row.addStretch()
        vl2.addLayout(png_bottom_row)

        # HasSubtitle checkbox
        sep4 = QFrame()
        sep4.setObjectName("CardSep")
        sep4.setFrameShape(QFrame.Shape.HLine)
        vl2.addWidget(sep4)

        sub_opt_row = QHBoxLayout()
        sub_opt_row.setSpacing(8)
        self.HasSubtitleCheck = QCheckBox("Có phụ đề")
        self.HasSubtitleCheck.setChecked(True)
        sub_opt_row.addWidget(self.HasSubtitleCheck)
        sub_opt_row.addStretch()
        vl2.addLayout(sub_opt_row)

        outer.addWidget(vg2, 1)
        outer.addStretch()
        return page

    # ---------------------------------------------------
    #  TAB 3: XỬ LÝ VIDEO & PHẦN CỨNG
    # ---------------------------------------------------
    def _build_process_tab(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(6, 14, 6, 6)
        outer.setSpacing(14)
        cols = QHBoxLayout()
        cols.setSpacing(18)

        # ---- Xử lý video ----
        vg3, vg3l = _make_card("Xử lý video", "🎛")
        vg3l.setSpacing(14)

        vg3l.addWidget(_section_label("ĐỘ SÁNG"))
        br_row = QHBoxLayout()
        br_row.setSpacing(8)
        br_row.addWidget(QLabel("−100"))
        self.BrightnessSlider = QSlider(Qt.Orientation.Horizontal)
        self.BrightnessSlider.setRange(-100, 100)
        self.BrightnessSlider.setValue(0)
        self.BrightnessLabel = QLabel("0")
        self.BrightnessLabel.setFixedWidth(34)
        self.BrightnessSlider.valueChanged.connect(lambda v: self.BrightnessLabel.setText(str(v)))
        br_row.addWidget(self.BrightnessSlider, 1)
        br_row.addWidget(QLabel("+100"))
        br_row.addSpacing(6)
        br_row.addWidget(self.BrightnessLabel)
        vg3l.addLayout(br_row)

        sep3 = QFrame()
        sep3.setObjectName("CardSep")
        sep3.setFrameShape(QFrame.Shape.HLine)
        vg3l.addWidget(sep3)

        vg3l.addWidget(_section_label("CẮT ĐẦU / CUỐI VIDEO"))
        cut_row1 = QHBoxLayout()
        cut_row1.setSpacing(8)
        cut_row1.addWidget(QLabel("Cắt đầu:"))
        self.CutStartSpin = QSpinBox()
        self.CutStartSpin.setRange(0, 600)
        self.CutStartSpin.setValue(0)
        self.CutStartSpin.setSuffix(" giây")
        cut_row1.addWidget(self.CutStartSpin, 1)
        vg3l.addLayout(cut_row1)

        cut_row2 = QHBoxLayout()
        cut_row2.setSpacing(8)
        cut_row2.addWidget(QLabel("Cắt cuối:"))
        self.CutEndSpin = QSpinBox()
        self.CutEndSpin.setRange(0, 600)
        self.CutEndSpin.setValue(0)
        self.CutEndSpin.setSuffix(" giây")
        cut_row2.addWidget(self.CutEndSpin, 1)
        vg3l.addLayout(cut_row2)
        vg3l.addStretch()

        cols.addWidget(vg3, 1)

        # ---- Phần cứng & chất lượng ----
        hg, hl = _make_card("Phần cứng & Chất lượng", "🖥")
        hl.setSpacing(14)

        hl.addWidget(_section_label("THIẾT BỊ XỬ LÝ"))
        hrow_stt = QHBoxLayout()
        hrow_stt.setSpacing(8)
        hrow_stt.addWidget(QLabel("STT:"))
        self.SttDeviceCombo = QComboBox()
        self.SttDeviceCombo.addItems(["cuda", "cpu"])
        hrow_stt.addWidget(self.SttDeviceCombo, 1)
        hl.addLayout(hrow_stt)

        hrow_rvc = QHBoxLayout()
        hrow_rvc.setSpacing(8)
        hrow_rvc.addWidget(QLabel("RVC:"))
        self.RvcDeviceCombo = QComboBox()
        self.RvcDeviceCombo.addItems(["cuda", "cpu"])
        hrow_rvc.addWidget(self.RvcDeviceCombo, 1)
        hl.addLayout(hrow_rvc)

        sep4 = QFrame()
        sep4.setObjectName("CardSep")
        sep4.setFrameShape(QFrame.Shape.HLine)
        hl.addWidget(sep4)

        hl.addWidget(_section_label("CHẤT LƯỢNG DỰNG"))
        hrow_render = QHBoxLayout()
        hrow_render.setSpacing(8)
        hrow_render.addWidget(QLabel("Render:"))
        self.RenderDeviceCombo = QComboBox()
        self.RenderDeviceCombo.addItems(["auto", "cuda (GPU)", "cpu"])
        hrow_render.addWidget(self.RenderDeviceCombo, 1)
        hl.addLayout(hrow_render)

        hrow_quality = QHBoxLayout()
        hrow_quality.setSpacing(8)
        hrow_quality.addWidget(QLabel("Preset:"))
        self.QualityCombo = QComboBox()
        self.QualityCombo.addItems(["p1", "p2", "p3", "p4", "p5", "p6", "p7"])
        self.QualityCombo.setCurrentText("p4")
        hrow_quality.addWidget(self.QualityCombo, 1)
        hl.addLayout(hrow_quality)
        hl.addStretch()

        cols.addWidget(hg, 1)
        outer.addLayout(cols)
        outer.addStretch()
        return page

    # ---------------------------------------------------
    #  FILE / CONFIG / RUN — logic giữ nguyên
    # ---------------------------------------------------
    def _on_png_slider_changed(self, value, field_name):
        """Cap nhat label va preview khi slider PNG thay doi"""
        # Cap nhat label
        if field_name == "pos_x":
            self.PngPosXLabel.setText(f"{value}%")
        elif field_name == "pos_y":
            self.PngPosYLabel.setText(f"{value}%")
        elif field_name == "width":
            self.PngWidthLabel.setText(f"{value}%")
        # Cap nhat preview neu dang mo
        if hasattr(self, 'PngPreview') and self.PngPreview.isVisible():
            pos_x = self.PngPosXSlider.value()
            pos_y = self.PngPosYSlider.value()
            width_percent = self.PngWidthSlider.value()
            anchor = self.PngAnchorCombo.currentText()
            aspect = self.AspectRatioCombo.currentText()
            png_path = self.PngPathEdit.text().strip()
            self.PngPreview.update_preview(pos_x, pos_y, width_percent, anchor, aspect, png_path)

    def _update_png_preview(self):
        """Cap nhat preview PNG neu dang mo"""
        if hasattr(self, 'PngPreview') and self.PngPreview.isVisible():
            pos_x = self.PngPosXSlider.value()
            pos_y = self.PngPosYSlider.value()
            width_percent = self.PngWidthSlider.value()
            anchor = self.PngAnchorCombo.currentText()
            aspect = self.AspectRatioCombo.currentText()
            png_path = self.PngPathEdit.text().strip()
            self.PngPreview.update_preview(pos_x, pos_y, width_percent, anchor, aspect, png_path)

    def _browse_png(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file PNG", "", "PNG Files (*.png);;All files (*)")
        if path:
            self.PngPathEdit.setText(path)
            # Tu dong cap nhat preview neu dang mo
            self._update_png_preview()

    def _show_png_preview(self):
        if not hasattr(self, 'PngPreview'):
            self.PngPreview = PngOverlayPreviewDialog(self)
        if self.PngPreview.isVisible():
            self.PngPreview.hide()
            self.BtnPngPreview.setStyleSheet(_push_btn_style(COLOR_PRIMARY))
        else:
            pos_x = self.PngPosXSlider.value()
            pos_y = self.PngPosYSlider.value()
            width_percent = self.PngWidthSlider.value()
            anchor = self.PngAnchorCombo.currentText()
            aspect = self.AspectRatioCombo.currentText()
            png_path = self.PngPathEdit.text().strip()
            self.PngPreview.update_preview(pos_x, pos_y, width_percent, anchor, aspect, png_path)
            main_pos = self.pos()
            main_size = self.size()
            dialog_x = main_pos.x() + main_size.width() + 10
            dialog_y = main_pos.y()
            self.PngPreview.move(dialog_x, dialog_y)
            self.PngPreview.show()
            self.BtnPngPreview.setStyleSheet(_push_btn_style(COLOR_DANGER))

    def BrowseFile(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file danh sách link", "", "Text files (*.txt);;All files (*)")
        if path:
            self.FilePathInput.setText(path)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = [l.strip() for l in f if l.strip()]
                self.LogArea.append(f"Đã chọn file: {path} ({len(lines)} URL)")
            except:
                pass

    def GetCurrentConfig(self):
        if self.RadioGtts.isChecked():
            vt = "GTTS"
        elif self.RadioEdge.isChecked():
            vt = "EDGE"
        elif self.RadioTikTok.isChecked():
            vt = "TIKTOKTTS"
        elif self.RadioVietNeu.isChecked():
            vt = "VIENEU"
        elif self.RadioRvc.isChecked():
            vt = "RVC"
        else:
            vt = "EDGE"

        am = "mute" if self.RadioMute.isChecked() else "duck"
        bgm = self.BgmCombo.currentText() if self.BgmCheck.isChecked() and self.BgmCombo.count() > 0 else None
        te = "GEMINI" if self.RadioGemini.isChecked() else "FILTER"

        rb = self.RvcBaseCombo.currentText()
        if rb == "Edge TTS":
            rvc_b = "EDGE"
        elif rb == "Google TTS Free":
            rvc_b = "GTTS"
        else:
            rvc_b = "NEUTRAL"

        font_name = self.FontCombo.currentText()
        if self.custom_font_path:
            font_name = self.custom_font_path

        cfg = {
            "file_path": self.FilePathInput.text().strip(),
            "start_index": self.StartIndexSpin.value(),
            "max_concurrent": self.ParallelSpin.value(),
            "speed": 1.0,
            "voice_type": vt,
            "rvc_model": self.ModelCombo.currentText() if self.ModelCombo.count() > 0 else "",
            "rvc_base": rvc_b,
            "rvc_mode": self.RvcModeCombo.currentText().lower(),
            "f0_key": self.F0Spin.value(),
            "edge_voice": self.EdgeVoiceCombo.currentText().split(" (")[0],
            "neutral_voice": self.NeutralVoiceCombo.currentText().split(" (")[0],
            "audio_mode": am,
            "bgm_file": bgm,
            "voice_rate": self.VoiceRateSlider.value() / 10.0,
            "gtts_rate": self.GttsRateSlider.value() / 10.0,
            "dvoice_rate": self.DVoiceRateSlider.value() / 10.0,
            "edge_rate": self.EdgeRateInput.text().strip() or "+25%",
            "trans_engine": te,
            "mood": self.StyleCombo.currentText(),
            "source_lang": self.LangCombo.currentText(),
            "blur_sub": self.BlurCheck.isChecked(),
            "subtitle_position": "auto_blur",
            "font_size": self.FontSizeSpin.value(),
            "blur_start_percent": self.BlurStartSlider.value(),
            "blur_end_percent": self.BlurEndSlider.value(),
            "blur_intensity": self.BlurIntensitySlider.value(),
            "aspect_ratio": self.AspectRatioCombo.currentText(),
            "font_name": font_name,
            "font_color": self._font_color.name(),
            "outline_color": self._outline_color.name(),
            "sub_background": self.SubBgCheck.isChecked(),
            "back_color": self._back_color.name(),
            "stt_device": self.SttDeviceCombo.currentText(),
            "rvc_device": self.RvcDeviceCombo.currentText(),
            "render_device": self.RenderDeviceCombo.currentText().split()[0],
            "quality": self.QualityCombo.currentText(),
            "stt_model": self.SttModelCombo.currentText(),
            "tiktok_voice": self.TikTokVoiceCombo.currentText(),
            "brightness": self.BrightnessSlider.value(),
            "cut_start": self.CutStartSpin.value(),
            "cut_end": self.CutEndSpin.value(),
            "enable_png_overlay": self.PngOverlayCheck.isChecked(),
            "png_path": self.PngPathEdit.text().strip(),
            "png_pos_x": self.PngPosXSlider.value(),
            "png_pos_y": self.PngPosYSlider.value(),
            "png_anchor": self.PngAnchorCombo.currentText(),
            "png_width_percent": self.PngWidthSlider.value(),
            "png_start_time": self.PngStartTimeSpin.value(),
            "png_end_time": self.PngEndTimeSpin.value(),
            "png_full_video": self.PngFullVideoCheck.isChecked(),
            "has_subtitle": self.HasSubtitleCheck.isChecked(),
        }
        # Key nay khong co tren UI: giu gia tri nguoi dung sua truc tiep trong JSON,
        # tranh bi ghi de moi lan Save/dong app.
        cfg["gemini_max_retries"] = self.saved_config.get("gemini_max_retries", 5)
        return cfg

    def RestoreConfig(self):
        c = self.saved_config
        if not c:
            return
        try:
            if c.get("file_path"):
                self.FilePathInput.setText(c["file_path"])
            for k, sp in [("start_index", self.StartIndexSpin),
                          ("max_concurrent", self.ParallelSpin),
                          ("f0_key", self.F0Spin),
                          ("font_size", self.FontSizeSpin)]:
                if k in c:
                    sp.setValue(c[k])
            if "voice_rate" in c:
                self.VoiceRateSlider.setValue(int(c["voice_rate"] * 10))
            if "gtts_rate" in c:
                self.GttsRateSlider.setValue(int(c["gtts_rate"] * 10))
            if "dvoice_rate" in c:
                self.DVoiceRateSlider.setValue(int(c["dvoice_rate"] * 10))
            if "edge_rate" in c:
                self.EdgeRateInput.setText(c["edge_rate"])
            if "voice_type" in c:
                vt = c["voice_type"]
                if vt == "GTTS":
                    self.RadioGtts.setChecked(True)
                elif vt == "EDGE":
                    self.RadioEdge.setChecked(True)
                elif vt == "TIKTOKTTS":
                    self.RadioTikTok.setChecked(True)
                elif vt == "VIENEU":
                    self.RadioVietNeu.setChecked(True)
                elif vt == "RVC":
                    self.RadioRvc.setChecked(True)
            if "rvc_base" in c:
                rb = c["rvc_base"]
                if rb == "EDGE":
                    self.RvcBaseCombo.setCurrentText("Edge TTS")
                elif rb == "GTTS":
                    self.RvcBaseCombo.setCurrentText("Google TTS Free")
                else:
                    self.RvcBaseCombo.setCurrentText("Google Cloud Token")
            if c.get("rvc_mode"):
                self.RvcModeCombo.setCurrentText(c["rvc_mode"].capitalize())
            for k, co in [("neutral_voice", self.NeutralVoiceCombo),
                          ("edge_voice", self.EdgeVoiceCombo),
                          ("rvc_model", self.ModelCombo),
                          ("stt_model", self.SttModelCombo),
                          ("quality", self.QualityCombo),
                          ("aspect_ratio", self.AspectRatioCombo),
                          ("font_name", self.FontCombo),
                          ("tiktok_voice", self.TikTokVoiceCombo)]:
                if c.get(k):
                    idx = co.findText(c[k])
                    if idx >= 0:
                        co.setCurrentIndex(idx)
            if "blur_start_percent" in c:
                self.BlurStartSlider.setValue(c["blur_start_percent"])
            if "blur_end_percent" in c:
                self.BlurEndSlider.setValue(c["blur_end_percent"])
            if "blur_intensity" in c:
                self.BlurIntensitySlider.setValue(c["blur_intensity"])
            if c.get("stt_device"):
                idx = self.SttDeviceCombo.findText(c["stt_device"])
                if idx >= 0:
                    self.SttDeviceCombo.setCurrentIndex(idx)
            if c.get("rvc_device"):
                idx = self.RvcDeviceCombo.findText(c["rvc_device"])
                if idx >= 0:
                    self.RvcDeviceCombo.setCurrentIndex(idx)
            if c.get("render_device"):
                idx = self.RenderDeviceCombo.findText(c["render_device"])
                if idx >= 0:
                    self.RenderDeviceCombo.setCurrentIndex(idx)
            if "blur_sub" in c:
                self.BlurCheck.setChecked(c["blur_sub"])
            if c.get("trans_engine") == "GEMINI":
                self.RadioGemini.setChecked(True)
            else:
                self.RadioFilter.setChecked(True)
            if c.get("mood"):
                idx = self.StyleCombo.findText(c["mood"])
                if idx >= 0:
                    self.StyleCombo.setCurrentIndex(idx)
            if c.get("source_lang"):
                idx = self.LangCombo.findText(c["source_lang"])
                if idx >= 0:
                    self.LangCombo.setCurrentIndex(idx)
            if c.get("font_color"):
                self._font_color = QColor(c["font_color"])
                self._update_color_btn(self.FontColorBtn, self._font_color)
            if c.get("outline_color"):
                self._outline_color = QColor(c["outline_color"])
                self._update_color_btn(self.OutlineColorBtn, self._outline_color)
            if c.get("back_color"):
                self._back_color = QColor(c["back_color"])
                self._update_color_btn(self.BackColorBtn, self._back_color)
            if "brightness" in c:
                self.BrightnessSlider.setValue(c["brightness"])
            if "cut_start" in c:
                self.CutStartSpin.setValue(c["cut_start"])
            if "cut_end" in c:
                self.CutEndSpin.setValue(c["cut_end"])
            self.LogArea.append(f"Đã khôi phục cấu hình từ {CONFIG_FILE}")
        except Exception as e:
            self.LogArea.append(f"Lỗi khôi phục cấu hình: {e}")

    def SaveCurrentConfig(self):
        config = self.GetCurrentConfig()
        save_config(config)
        self.saved_config = config
        QMessageBox.information(self, "Thành công", f"Đã lưu cấu hình vào {CONFIG_FILE}")

    def ExportConfig(self):
        config = self.GetCurrentConfig()
        if export_config_to_file(config):
            QMessageBox.information(self, "Thành công", "Đã xuất cấu hình thành công!")

    def ImportConfig(self):
        config = import_config_from_file()
        if config:
            self.saved_config = config
            save_config(config)
            self.RestoreConfig()
            QMessageBox.information(self, "Thành công", "Đã nhập cấu hình thành công!")

    def ResetConfig(self):
        self.FilePathInput.clear()
        self.StartIndexSpin.setValue(1)
        self.ParallelSpin.setValue(2)
        self.RadioEdge.setChecked(True)
        self.EdgeVoiceCombo.setCurrentIndex(0)
        self.NeutralVoiceCombo.setCurrentIndex(0)
        self.EdgeRateInput.setText("+25%")
        self.VoiceRateSlider.setValue(16)
        self.GttsRateSlider.setValue(19)
        self.DVoiceRateSlider.setValue(10)
        self.RadioDuck.setChecked(True)
        self.BgmCheck.setChecked(False)
        self.RadioFilter.setChecked(True)
        self.StyleCombo.setCurrentIndex(0)
        self.LangCombo.setCurrentIndex(0)
        self.F0Spin.setValue(8)
        self.BlurCheck.setChecked(True)
        self.AspectRatioCombo.setCurrentText("auto")
        self.FontSizeSpin.setValue(32)
        self.BlurStartSlider.setValue(80)
        self.BlurEndSlider.setValue(95)
        if self.FontCombo.count() > 0:
            self.FontCombo.setCurrentText("Arial")
        self.custom_font_path = None
        self._font_color = QColor("#FFFF00")
        self._update_color_btn(self.FontColorBtn, self._font_color)
        self._outline_color = QColor("#000000")
        self._update_color_btn(self.OutlineColorBtn, self._outline_color)
        self._back_color = QColor("#80000000")
        self._update_color_btn(self.BackColorBtn, self._back_color)
        self.SttDeviceCombo.setCurrentIndex(0)
        self.RvcDeviceCombo.setCurrentIndex(0)
        self.RenderDeviceCombo.setCurrentIndex(0)
        self.QualityCombo.setCurrentText("p4")
        self.SttModelCombo.setCurrentText("small")
        self.RvcModeCombo.setCurrentText("docker")
        self.BrightnessSlider.setValue(0)
        self.CutStartSpin.setValue(0)
        self.CutEndSpin.setValue(0)
        self.LogArea.append("Đặt lại về mặc định")

    def StartAutomation(self):
        config = self.GetCurrentConfig()
        if not config["file_path"] or not os.path.exists(config["file_path"]):
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file danh sách link hợp lệ!")
            return
        if config["voice_type"] == "GTTS" or (config["voice_type"] == "RVC" and config["rvc_base"] == "NEUTRAL"):
            if not os.path.exists("service-account.json"):
                # Vẫn cho workflow resume: task đã render xong không cần token.
                # Controller chỉ kiểm tra token nếu thật sự phải chạy lại B4.
                self.LogArea.append(
                    "CẢNH BÁO: chưa có service-account.json; "
                    "các task cần chạy mới bước render Google TTS sẽ tạm lỗi."
                )

        self.BtnStart.setEnabled(False)
        self.BtnStart.setText("⏳  ĐANG XỬ LÝ...")
        self.Progress.setValue(0)
        self.LogArea.append("\n" + "="*50)
        self.LogArea.append(f"BẮT ĐẦU CHẠY: {config['max_concurrent']} luồng song song")
        self.worker = AutomationWorker(config, self.controller)
        self.worker.LogSignal.connect(lambda m: self.LogArea.append(m))
        self.worker.ProgressSignal.connect(self.Progress.setValue)
        self.worker.FinishedSignal.connect(self.OnFinished)
        self.worker.start()

    def OnFinished(self, success, total):
        self.BtnStart.setEnabled(True)
        self.BtnStart.setText("▶   BẮT ĐẦU CHẠY HÀNG LOẠT")
        self.LogArea.append("="*50)
        self.LogArea.append(f"HOÀN TẤT: {success}/{total} video thành công!")
        QMessageBox.information(self, "Hoàn tất", f"Xử lý xong {success}/{total} video!")

    def closeEvent(self, event):
        worker = getattr(self, "worker", None)
        if worker is not None and worker.isRunning():
            reply = QMessageBox.question(
                self, "Đang xử lý",
                "Đang xử lý video. Dừng và thoát?\n"
                "Tiến độ đã được lưu; lần sau bấm Bắt đầu sẽ chạy tiếp.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.LogArea.append("Đang dừng tiến trình con và lưu tiến độ...")
            worker.stop()
            self.controller.terminate_children()
            worker.wait(5000)

        try:
            save_config(self.GetCurrentConfig())
        except:
            pass
        if hasattr(self, 'BlurPreview') and self.BlurPreview.isVisible():
            self.BlurPreview.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AutomationWindow()
    window.show()
    sys.exit(app.exec())
