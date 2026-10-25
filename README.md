# reupvideo

Công cụ tạo lại video ngắn từ danh sách link hoặc video local: nhận dạng lời thoại, dịch sang tiếng Việt, lồng tiếng và render video có phụ đề.

## Xem trước

Ví dụ `links.txt`:

```text
https://www.douyin.com/video/123
/home/user/videos/demo.mp4
```

Sau khi chạy, kết quả nằm trong `final_output/`:

```text
final_output/tap1.mp4
final_output/tap2.mp4
```

## Bắt đầu nhanh

Yêu cầu: Python 3.10 trở lên (đã test với 3.12), FFmpeg và ffprobe trong `PATH` (đã test với FFmpeg 6.1). GPU NVIDIA là tuỳ chọn.

Cài FFmpeg nếu chưa có: `sudo apt install ffmpeg` trên Ubuntu/Debian hoặc `brew install ffmpeg` trên macOS. Trên Windows, tải bản build và thêm thư mục `bin` vào `PATH`.

```bash
git clone git@github.com:nightrain09/re-up_videos.git
cd re-up_videos

python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install PyQt6 faster-whisper playwright moviepy
playwright install chromium
```

Tạo file `.env` ở thư mục gốc:

```env
GEMINI_API_KEYS=key1,key2
GEMINI_MODELS=gemini-2.0-flash
VIETPHRASE_DEFAULT_TOKEN=
```

Chạy giao diện:

```bash
python AutomationApp.py
```

Nếu dùng giọng TikTok, chạy CapCut TTS ở terminal khác:

```bash
cd CapCut-TTS
npm install
cp .env.example .env
npm run dev
```

Server chạy tại `http://localhost:8080`. Với RVC native, cài thêm `pip install rvc-python`; với RVC docker, cần Docker. Google Cloud TTS cần `service-account.json` trong thư mục gốc.

## Cách dùng

1. Tạo `links.txt`, mỗi dòng một link hoặc đường dẫn video local.
2. Mở ứng dụng, chọn file này ở mục `Danh sách link / video`.
3. Đặt `Bắt đầu từ` và `Song song`, chỉnh các tab cấu hình.
4. Bấm `Bắt đầu chạy hàng loạt`.

Kết quả nằm trong `final_output/tap<số>.mp4`. Task đang dở sẽ chạy tiếp nếu mở lại và bấm Bắt đầu.

Có thể chạy riêng từng bước:

```bash
# STT
python stt.py --input input.mp4 --output stt_raw.txt --lang zh --model small --device cuda

# Dịch bằng Gemini
python gemini_trans.py --input stt_raw.txt --output filtered.txt --lang zh --max-retries 5
```

`stt_raw.txt` và `filtered.txt` dùng định dạng `[hh:mm:ss,mmm] nội dung`.

## Cấu hình

Ứng dụng đọc `automation_config.json` khi mở và ghi lại khi bấm `Lưu cấu hình` hoặc đóng app. `config.json` chỉ là file xuất/nhập cấu hình; app không tự đọc. `automation_config.example.json` là mẫu đầy đủ, có `_description` giải thích từng trường.

### Biến môi trường

| Biến | Mô tả | Mặc định | Bắt buộc |
|------|-------|----------|----------|
| `GEMINI_API_KEYS` | Danh sách key Gemini, cách nhau dấu phẩy | Không | Có nếu dùng Gemini |
| `GEMINI_MODELS` | Danh sách model Gemini, cách nhau dấu phẩy | Không | Có nếu dùng Gemini |
| `VIETPHRASE_DEFAULT_TOKEN` | Token VietPhrase cho chế độ Bộ lọc | Rỗng | Có nếu dùng Bộ lọc |

### Tùy chọn chính trong `automation_config.json`

| Khóa | Mô tả | Mặc định |
|------|-------|----------|
| `file_path` | File `.txt` chứa danh sách link/video | Phải chọn |
| `start_index` | Số thứ tự bắt đầu | `1` |
| `max_concurrent` | Số video chạy song song, 1-10 | `2` |
| `voice_type` | Nguồn giọng: `EDGE`, `GTTS`, `TIKTOKTTS`, `VIENEU`, `RVC` | `EDGE` |
| `trans_engine` | `GEMINI` hoặc `FILTER` | `FILTER` |
| `source_lang` | Ngôn ngữ nguồn: `zh`, `en`, `ja`, `ko`, `vi` | `zh` |
| `mood` | Kiểu xưng hô cho Bộ lọc: `tinh_cam`, `hai_huoc`, `giang_ho`, `xa_giao` | `tinh_cam` |
| `gemini_max_retries` | Số lần thử lại khi Gemini sai định dạng; `0` hoặc `-1` là vô tận | `5` |
| `stt_model` | Model STT: `tiny`, `base`, `small`, `medium`, `large-v3` | `small` |
| `quality` | Chất lượng render từ `p1` đến `p7` | `p4` |
| `render_device` | `auto`, `cuda`, `cpu` | `auto` |
| `aspect_ratio` | `auto`, `16:9`, `9:16` | `auto` |
| `blur_sub` | Làm mờ phụ đề cũ | `true` |
| `enable_png_overlay` | Chèn ảnh PNG | `false` |
| `audio_mode` | `duck` hoặc `mute` | `duck` |
| `has_subtitle` | Hiển thị phụ đề | `true` |

Các trường còn lại như blur, font, màu, PNG, cắt video và RVC được giải thích trong `automation_config.example.json`.

Sửa cấu hình: chỉnh trên giao diện rồi bấm `Lưu cấu hình`, hoặc đóng app, sửa `automation_config.json` rồi mở lại. Để dùng nhiều bộ cấu hình, dùng `Xuất config` và `Nhập config`.

## Cấu trúc

- `AutomationApp.py`: giao diện PyQt6.
- `MainController.py`: điều phối các bước xử lý.
- `stt.py`: nhận dạng giọng nói bằng faster-whisper.
- `gemini_trans.py`: dịch Gemini, kiểm tra định dạng và retry.
- `filter.py`: bộ lọc xưng hô cho chế độ Bộ lọc.
- `pre_process_video.py`: tiền xử lý video.
- `subVideo_gg.py`: render với Edge, gTTS, Google Cloud, TikTok.
- `subVideo_rvc.py`: render với RVC.
- `subVideo_vietNeu.py`: render với VieNeu.
- `subVideo_png_overlay.py`: chèn ảnh PNG.
- `utils/`: thư viện dùng chung.
- `CapCut-TTS/`: server TTS cho giọng TikTok.
- `automation_config.example.json`: mẫu cấu hình đầy đủ.
- `requirements.txt`: thư viện Python.
