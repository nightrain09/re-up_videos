import collections
import os
import argparse
import sys
import gc
import threading

# Fix cho Python 3.10+
if not hasattr(collections, 'MutableSet'):
    import collections.abc
    collections.MutableSet = collections.abc.MutableSet
    collections.Mapping = collections.abc.Mapping
    collections.MutableMapping = collections.abc.MutableMapping
    collections.Iterable = collections.abc.Iterable
    collections.MutableSequence = collections.abc.MutableSequence

from faster_whisper import WhisperModel

try:
    from moviepy.editor import VideoFileClip
except ImportError:
    from moviepy import VideoFileClip

# Mỗi device chỉ có một model dùng chung cho toàn bộ process.
_MODELS = {}
_MODEL_LOCK = threading.Lock()


class _GpuAdmission:
    """Giới hạn CUDA thích nghi: bắt đầu tối đa, giảm sau mỗi lần OOM."""

    def __init__(self, capacity):
        self.capacity = max(1, int(capacity))
        self.active = 0
        self.lock = threading.Lock()

    def try_acquire(self):
        with self.lock:
            if self.capacity <= 0 or self.active >= self.capacity:
                return None
            self.active += 1
            # Token ghi lại mức giới hạn mà tác vụ đã được nhận vào.
            return self.capacity

    def release(self):
        with self.lock:
            self.active = max(0, self.active - 1)

    def reduce_after_oom(self, admitted_capacity):
        with self.lock:
            # Nhiều tác vụ có thể cùng nhận một lỗi OOM. Chỉ giảm một lần cho
            # các lỗi thuộc cùng mức giới hạn đã quan sát.
            if self.capacity >= admitted_capacity:
                self.capacity = max(0, admitted_capacity - 1)
            return self.capacity

    def get_capacity(self):
        with self.lock:
            return self.capacity


_GPU_ADMISSIONS = {}
_GPU_ADMISSIONS_LOCK = threading.Lock()


def _get_gpu_admission(model_size, num_workers):
    key = (model_size, max(1, int(num_workers)))
    with _GPU_ADMISSIONS_LOCK:
        admission = _GPU_ADMISSIONS.get(key)
        if admission is None:
            admission = _GpuAdmission(num_workers)
            _GPU_ADMISSIONS[key] = admission
        return admission


def get_model(model_size="small", device="cuda", num_workers=1):
    """Lấy model dùng chung; mỗi device chỉ giữ một model cho cùng cấu hình."""

    num_workers = max(1, int(num_workers))
    config = (model_size, device, num_workers)
    cached = _MODELS.get(device)

    if cached is not None and cached[0] == config:
        return cached[1]

    with _MODEL_LOCK:
        cached = _MODELS.get(device)
        if cached is not None and cached[0] == config:
            return cached[1]

        if cached is not None:
            print(f"--- Releasing old Whisper model {cached[0]}... ---")
            del _MODELS[device]
            gc.collect()

        print(
            f"--- Initializing shared Whisper {device} ({model_size}), "
            f"parallel workers={num_workers}... ---"
        )
        model = WhisperModel(
            model_size,
            device=device,
            compute_type="int8",
            num_workers=num_workers,
        )
        _MODELS[device] = (config, model)
        return model


def format_timestamp(seconds):
    ms = int((seconds - int(seconds)) * 1000)
    full_seconds = int(seconds)
    hours = full_seconds // 3600
    minutes = (full_seconds % 3600) // 60
    secs = full_seconds % 60
    return f"[{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}]"


def _transcribe_to_file(model, audio_path, output_path, language):
    segments, info = model.transcribe(
        audio_path,
        language=language,
        vad_filter=True,
        beam_size=8
    )

    print(f"--- 4. Writing results to {output_path}... ---")
    tmp_path = output_path + ".part"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            # segments là generator: việc inference thực sự diễn ra khi lặp ở đây.
            for segment in segments:
                ts_str = format_timestamp(segment.start)
                text = segment.text.strip()
                if text:
                    line = f"{ts_str} {text}"
                    f.write(line + "\n")
                    print(f"[STT] {line}")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, output_path)
    except Exception:
        # Mất điện / lỗi giữa chừng: bỏ file dở, không để resume nhầm.
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def _is_cuda_oom(error):
    message = str(error).lower()
    return "out of memory" in message and ("cuda" in message or "gpu" in message)


def process_video(input_path, output_path, device="cuda", language="zh", model_size="small", num_workers=1):
    audio_temp = f"{input_path}_temp.mp3"
    video = None
    gpu_admission = None
    gpu_admission_token = None
    num_workers = max(1, int(num_workers))

    print(f"--- 1. Extracting audio from {input_path}... ---")
    try:
        video = VideoFileClip(input_path)
        video.audio.write_audiofile(audio_temp, logger=None)
    except Exception as e:
        print(f"ERROR Moviepy: {e}")
        if video is not None:
            video.close()
        if os.path.exists(audio_temp):
            os.remove(audio_temp)
        return False

    try:
        selected_device = device
        model_workers = num_workers

        # Ban đầu cho phép toàn bộ số luồng đã chọn dùng CUDA. Chỉ sau khi OOM
        # mới hạ giới hạn và chuyển phần vượt giới hạn sang CPU.
        if device == "cuda":
            gpu_admission = _get_gpu_admission(model_size, num_workers)
            gpu_admission_token = gpu_admission.try_acquire()
            if gpu_admission_token is not None:
                model_workers = gpu_admission_token
                print(
                    f"--- STT route: GPU "
                    f"(adaptive limit={gpu_admission.get_capacity()}/{num_workers}) ---"
                )
            else:
                selected_device = "cpu"
                model_workers = max(1, num_workers - gpu_admission.get_capacity())
                print("--- STT route: CPU (adaptive CUDA limit reached) ---")

        model = None
        try:
            print(f"--- 2. Getting shared Whisper {selected_device} ({model_size})... ---")
            model = get_model(model_size, selected_device, model_workers)
            print(f"--- 3. Transcribing on {selected_device} (Language: {language})... ---")
            _transcribe_to_file(model, audio_temp, output_path, language)
        except Exception as error:
            if selected_device != "cuda" or not _is_cuda_oom(error):
                raise

            new_limit = gpu_admission.reduce_after_oom(gpu_admission_token)
            print(
                f"--- CUDA OOM: reducing GPU concurrency to {new_limit}/{num_workers}; "
                f"retrying this task: {error} ---"
            )
            if gpu_admission_token is not None:
                gpu_admission.release()
                gpu_admission_token = None

            # Bỏ reference model cũ trước khi có thể nạp lại với ít worker hơn.
            model = None
            gc.collect()

            # Nếu GPU đã rảnh, thử lại chính tác vụ này với giới hạn mới. Nếu
            # tác vụ GPU khác còn chạy, chuyển tác vụ lỗi sang CPU ngay.
            if new_limit > 0:
                gpu_admission_token = gpu_admission.try_acquire()
            if gpu_admission_token is not None:
                print(f"--- STT retry route: GPU (limit={new_limit}/{num_workers}) ---")
                try:
                    retry_model = get_model(model_size, "cuda", gpu_admission_token)
                    _transcribe_to_file(retry_model, audio_temp, output_path, language)
                except Exception as retry_error:
                    if not _is_cuda_oom(retry_error):
                        raise
                    new_limit = gpu_admission.reduce_after_oom(gpu_admission_token)
                    gpu_admission.release()
                    gpu_admission_token = None
                    print(
                        f"--- CUDA still OOM at reduced limit; "
                        f"retrying on CPU: {retry_error} ---"
                    )

            if gpu_admission_token is None:
                cpu_workers = max(1, num_workers - new_limit)
                print(f"--- STT retry route: CPU (workers={cpu_workers}) ---")
                cpu_model = get_model(model_size, "cpu", cpu_workers)
                _transcribe_to_file(cpu_model, audio_temp, output_path, language)

        print("--- DONE ---")
        return True
    except Exception as e:
        print(f"ERROR Whisper STT: {e}")
        return False
    finally:
        if gpu_admission_token is not None:
            gpu_admission.release()
        if video is not None:
            video.close()
        if os.path.exists(audio_temp):
            os.remove(audio_temp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Whisper STT")
    parser.add_argument("--input", required=True, help="Input video path")
    parser.add_argument("--output", required=True, help="Output txt path")
    parser.add_argument("--device", default="cuda", help="Device: cuda or cpu")
    parser.add_argument("--lang", default="zh", help="Source language")
    parser.add_argument("--model", default="small", help="Model size: tiny/base/small/medium/large-v3")
    parser.add_argument("--workers", type=int, default=1, help="Parallel transcription workers")
    args = parser.parse_args()

    if os.path.exists(args.input):
        success = process_video(args.input, args.output, args.device, args.lang, args.model, args.workers)
        if not success:
            sys.exit(1)
    else:
        print(f"ERROR: File not found {args.input}")
        sys.exit(1)
