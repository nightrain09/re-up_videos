# 🎬 MMO SubVideo AI

> **Dự án xử lý video tự động:** Speech-to-Text → Dịch thuật (Gemini AI) → Render Video với giọng đọc AI (Edge TTS, Google TTS, TikTok TTS, RVC Voice Clone)

---

## ✨ Tính năng chính

| Tính năng | Mô tả |
|-----------|-------|
| 🎤 **Speech-to-Text** | Whisper (faster-whisper), chọn model **tiny/base/small/medium/large-v3** |
| 🌐 **Dịch thuật** | **Gemini AI** (xoay vòng key tự động) hoặc VietPhrase API |
| 🗣️ **Text-to-Speech** | Edge TTS, Google TTS, Google Cloud, TikTok TTS (CapCut) |
| 🤖 **AI Voice Clone** | RVC (Docker hoặc Native, chọn model từ giao diện) |
| 🔄 **Lách bản quyền** | Flip, color shift, crop, MD5 bypass tự động |
| 🖥️ **GPU/CPU** | Tự động phát hiện, user tự chọn **auto/cuda/cpu** |
| ⭐ **Chất lượng** | **fast/medium/high** — preset + bitrate tương ứng |
| 🎯 **Subtitle** | 7 vị trí, chỉnh cỡ chữ, màu chữ, màu viền, font chữ |
| 🔄 **Tỷ lệ khung hình** | Chọn tay **auto / 16:9 / 9:16** |
| 🌫️ **Blur thông minh** | Chọn **khoảng %** blur (VD: từ 80% đến 95%) thay vì margin cứng |
| 🔤 **Font chữ tùy chỉnh** | Font hệ thống sẵn có + tải file **.ttf** bên ngoài |
| 🎨 **Màu chữ & viền** | Tuỳ chỉnh màu chữ, màu viền subtitle |
| 📦 **Xuất/Nhập cấu hình** | Lưu/lưu lại cài đặt ra file **config.json** riêng |
| ⚡ **Chạy song song** | Xử lý 1-10 video cùng lúc (ThreadPoolExecutor) |
| 📊 **Progress + Log** | Progress bar realtime, log area |
| 🎬 **Single Task** | Xử lý từng video riêng lẻ |
| 🤖 **Automation** | Chọn file danh sách link, chạy hàng loạt |

---

## 🖥️ Giao diện

### Tab 1: Tác vụ đơn (Single Task)
- Dán URL / chọn file video
- Cấu hình giọng nói, dịch thuật, STT
- **Video & Phụ đề**: Chọn tỷ lệ khung hình, vị trí sub, cỡ chữ
- **Blur**: Kéo thanh "Mờ từ X% đến Y%" để chọn vùng blur
- **Font**: Chọn font từ danh sách hoặc nhấn "Chọn font..." để tải .ttf ngoài
- Bấm **BẮT ĐẦU TASK**

### Tab 2: Tự động (Automation)
- Chọn file .txt danh sách URL
- Cấu hình giống Single Task
- Chọn số video chạy cùng lúc
- **Nút Xuất config / Nhập config** để lưu cài đặt

### Phím tắt
- **F11**: Toàn màn hình

---

## ⚙️ Cài đặt

### Yêu cầu
- **Python 3.9+**, **FFmpeg** (bắt buộc)
- **GPU NVIDIA (CUDA)** khuyên dùng cho Whisper STT và RVC

### Cài đặt nhanh
```bash
# Clone
git clone <repo-url>
cd MMO

# Tạo môi trường ảo
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Cài thư viện
pip install -r requirements.txt

# Cài Playwright (cho download Douyin)
playwright install chromium

# Chạy
python App.py
```

### Cấu hình `.env`
Tạo file `.env` trong thư mục gốc:
```env
# === GEMINI API (bắt buộc nếu dùng Gemini dịch) ===
GEMINI_API_KEYS=AIzaSy...,AIzaSy...
GEMINI_MODELS=gemini-2.0-flash,gemini-3.1-flash-lite-preview,gemma-3-27b-it

# === GOOGLE CLOUD (nếu dùng Google Cloud TTS) ===
# Đặt file service-account.json trong thư mục gốc
```

### CapCut TTS (TikTok giọng đọc)
Project sử dụng CapCut TTS để lấy giọng đọc TikTok. Đây là một server riêng chạy bằng Node.js, cần được cài đặt và chạy song song.

#### Cài đặt CapCut TTS
```bash
cd CapCut-TTS

# Cài dependencies
npm install

# Tạo file .env từ mẫu
cp .env.example .env
```

#### Cấu hình CapCut TTS
Sửa file `CapCut-TTS/.env`, điền email/mật khẩu CapCut:
```env
CAPCUT_EMAIL=your-email@example.com
CAPCUT_PASSWORD=your-password

# Có thể để mặc định các thông số còn lại
```

#### Chạy CapCut TTS server
```bash
cd CapCut-TTS

# Chạy development
npm run dev

# Hoặc build & start production
npm run build
npm run start
```

Server sẽ chạy tại `http://localhost:8080`. Đảm bảo server này đang chạy **trước khi** dùng tính năng TikTok TTS trong App.py.

---

## 📂 Cấu trúc dự án

```
MMO/
├── App.py                    # GUI chính (2 tabs: Single + Automation)
├── AutomationApp.py          # GUI Automation (phiên bản độc lập)
├── MainController.py         # Điều phối workflow
├── stt.py                    # Speech-to-Text (Whisper, chọn model)
├── gemini_trans.py           # Dịch thuật Gemini AI (đọc key từ .env)
├── filter.py                 # Lọc/style nội dung (fix regex Unicode)
├── pre_process_video.py      # Tiền xử lý video (quality, device)
├── subVideo_gg.py            # Render TTS + sub (Edge/Google/TikTok)
├── subVideo_rvc.py           # Render RVC (Docker/Native mode)
├── subVideo_vietNeu.py       # Render VieNeu TTS
├── trans.py / transfile.py   # Gọi VietPhrase API dịch
├── TokenManager.py           # Quản lý token VietPhrase
├── automation.py             # Script chạy hàng loạt (độc lập)
│
├── utils/                    # Thư viện dùng chung
│   ├── audio.py              # speed_change, trim_silence
│   ├── subtitle.py           # parse_txt, ms_to_ass_time, generate_ass (hỗ trợ font, màu)
│   ├── ffmpeg.py             # get_video_duration, get_codec_config
│   ├── gpu_fallback.py       # Tự động fallback GPU→CPU khi lỗi
│   ├── tts_cache.py          # Cache TTS (tiết kiệm phí API)
│   └── video_profiles.py     # Blur %, aspect ratio, font, màu chữ
│
├── .gitignore                # Loại trừ credentials, models, output
├── requirements.txt          # Dependencies
├── README.md                 # Bạn đang đọc đây
└── ...
```

---

## 🚀 Hướng dẫn sử dụng chi tiết

### 1. Cấu hình Blur dạng khoảng %

**Trước đây (cũ):**
- Chọn "Margin V" (khoảng cách từ dưới lên): con số cứng 40px

**Bây giờ (mới):**
- **"Mờ từ X%"** - vị trí bắt đầu blur (tính từ trên xuống, VD: 80%)
- **"đến Y%"** - vị trí kết thúc blur (VD: 95%)
- Blur chỉ diễn ra trong khoảng này
- Subtitle hiển thị **ngay trong vùng blur**

Ví dụ: "Mờ từ 80% đến 95%" → 15% cuối video bị mờ, sub hiện ở 80-95%.

### 2. Chọn tỷ lệ khung hình

| Combo | Ý nghĩa |
|-------|---------|
| **auto** | Tự động phát hiện 16:9 hay 9:16 từ video |
| **16:9** | Ép dùng profile video ngang |
| **9:16** | Ép dùng profile video dọc (TikTok/Douyin) |

### 3. Chọn Font chữ

- **Combo Font chữ**: Danh sách font phổ biến (Arial, Tahoma, Roboto...)
- **Nút "Chọn font..."**: Mở hộp thoại cho phép:
  - Chọn font từ danh sách hệ thống đầy đủ
  - Hoặc nhấn "Chọn file font..." để tải file **.ttf** bên ngoài

### 4. Màu chữ & viền

Hiện tại mặc định:
- **Màu chữ**: Vàng (`#FFFF00`)
- **Màu viền**: Đen (`#000000`)
- **Chữ đậm**: Có (bold)

Bạn có thể sửa trực tiếp trong file config hoặc code nếu muốn đổi.

### 5. Xuất / Nhập cấu hình (AutomationApp.py)

| Nút | Chức năng |
|-----|-----------|
| **Lưu cấu hình** | Lưu vào `automation_config.json` (tự động tải lại lần sau) |
| **Đặt lại** | Reset tất cả về mặc định |
| **Xuất config** | Lưu cấu hình hiện tại ra file `.json` riêng (VD: `config_tiktok.json`) |
| **Nhập config** | Tải cấu hình từ file `.json` đã xuất trước đó |

### 6. Render device (GPU/CPU)

| Chọn | STT | RVC | FFmpeg |
|------|-----|-----|--------|
| **auto** | CUDA (nếu có) | CUDA (nếu có) | Tự detect NVENC |
| **cuda (GPU)** | CUDA | CUDA | h264_nvenc |
| **cpu** | CPU | CPU | libx264 (software) |

---

## 🐳 RVC Mode

| Mode | Yêu cầu | Dành cho |
|------|---------|----------|
| **docker** | Docker + GPU | Máy có Docker, cần isolate môi trường |
| **native** | `pip install rvc-python` | Máy không có Docker, chạy trực tiếp |

---

## 🎤 Model STT

| Model | Tốc độ | Độ chính xác | VRAM |
|-------|--------|--------------|------|
| tiny | ⚡ Cực nhanh | 🟢 Cơ bản | ~1GB |
| base | 🚀 Nhanh | 🟢 Khá | ~1GB |
| small | ✅ Cân bằng | 🟡 Tốt | ~2GB |
| medium | 🐢 Trung bình | 🟠 Rất tốt | ~5GB |
| large-v3 | 🐌 Chậm | 🔥 Tốt nhất | ~10GB |

---

## ⭐ Chất lượng render

| Chất lượng | GPU (NVENC) | CPU (libx264) | Dung lượng |
|-----------|-------------|---------------|-----------|
| fast | p1, CQ 28 | ultrafast, CRF 28 | ~2MB/phút |
| medium | p6, CQ 20 | medium, CRF 22 | ~8MB/phút |
| high | p7, CQ 16 | slow, CRF 18 | ~16MB/phút |

---

## 🔧 Troubleshooting

| Lỗi | Nguyên nhân | Fix |
|-----|------------|-----|
| `Không tìm thấy file service-account.json` | Thiếu Google Cloud token | Đặt file vào thư mục gốc |
| `CUDA out of memory` | Hết VRAM | Giảm STT model, hoặc dùng CPU |
| `Unknown encoder 'h264_nvenc'` | GPU không hỗ trợ NVENC | Chọn thiết bị "cpu" |
| `403 Forbidden` (VietPhrase) | Token hết hạn | Chạy `getTransToken.py` lấy token mới |
| `No module named 'rvc_python'` | Chưa cài RVC | Chọn RVC mode "docker" hoặc `pip install rvc-python` |
| Blur không đúng vị trí | Sai tỷ lệ khung hình | Chọn đúng 16:9 (ngang) hay 9:16 (dọc) |
| Font không hiển thị | Font không hỗ trợ Unicode | Chọn font hỗ trợ tiếng Việt (Arial, Tahoma, Roboto...) |

---

## 📦 Build EXE (Windows)
```bash
pip install pyinstaller
pyinstaller App.spec
```
File exe sẽ nằm trong `dist/App/`. Người dùng cần copy thư mục `rvc/`, `bgm/` và `service-account.json` vào cùng thư mục với `App.exe`.

---

## 📝 Ghi chú phiên bản

### thay đổi gần đây:
- ✅ **Blur dạng khoảng %**: "Mờ từ X% đến Y%" thay vì margin cứng
- ✅ **Tỷ lệ khung hình thủ công**: Combo auto / 16:9 / 9:16
- ✅ **Font chữ tùy chỉnh**: Hỗ trợ font hệ thống + file .ttf ngoài
- ✅ **Màu chữ & viền**: Tuỳ chỉnh màu subtitle
- ✅ **Xuất/Nhập config**: Lưu cài đặt ra file .json riêng
- ✅ **Giao diện tiếng Việt có dấu**