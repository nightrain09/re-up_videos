import functools
import gc


def detect_gpu_health():
    """
    Kiểm tra sức khỏe GPU trước khi chạy task.
    Trả về: "healthy", "low_memory", "unavailable"
    """
    try:
        import torch
        if not torch.cuda.is_available():
            return "unavailable"

        free_mem, total_mem = torch.cuda.mem_get_info()
        free_gb = free_mem / 1024 ** 3

        if free_gb < 1.0:
            return "low_memory"
        return "healthy"
    except Exception:
        return "unavailable"


def auto_fallback_to_cpu(retry_count=1):
    """
    Decorator: Tự động fallback GPU -> CPU nếu gặp lỗi CUDA/NVENC.
    Khi chạy với device='cuda' mà lỗi OOM -> clear cache -> chuyển CPU -> chạy lại.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            device = kwargs.get("device", "cuda")
            if device != "cuda":
                return func(*args, **kwargs)

            for attempt in range(retry_count + 1):
                try:
                    return func(*args, **kwargs)

                except torch.cuda.OutOfMemoryError as e:
                    print(f"[GPU] CUDA OOM (lần {attempt + 1}): {e}")
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()
                    gc.collect()
                    kwargs["device"] = "cpu"

                except RuntimeError as e:
                    err = str(e).lower()
                    if "out of memory" in err or "cuda" in err:
                        print(f"[GPU] Runtime Error (lần {attempt + 1}): {e}")
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                        gc.collect()
                        kwargs["device"] = "cpu"
                    else:
                        raise

                except Exception as e:
                    err = str(e).lower()
                    if "nvenc" in err or "cuda" in err:
                        print(f"[GPU] FFmpeg Error (lần {attempt + 1}): {e}")
                        kwargs["device"] = "cpu"
                    else:
                        raise

            print(f"[GPU] Da thu {retry_count + 1} lan van loi. Dung task.")
            return None
        return wrapper
    return decorator


class TaskScheduler:
    """Điều phối số lượng task GPU đồng thời. Tự động fallback CPU nếu quá tải."""

    def __init__(self, max_concurrent_gpu=1):
        self.max_concurrent_gpu = max_concurrent_gpu
        self.active_gpu_tasks = 0
        self.lock = __import__('threading').Lock()

    def acquire_gpu(self, timeout=120):
        """Chờ đến khi có slot GPU. Timeout -> fallback CPU."""
        import time
        start = time.time()
        while time.time() - start < timeout:
            with self.lock:
                if self.active_gpu_tasks < self.max_concurrent_gpu:
                    self.active_gpu_tasks += 1
                    return True
            time.sleep(5)
        return False

    def release_gpu(self):
        with self.lock:
            self.active_gpu_tasks = max(0, self.active_gpu_tasks - 1)


# Singleton cho toàn bộ app
_scheduler = None


def get_scheduler(max_concurrent=1):
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler(max_concurrent)
    return _scheduler