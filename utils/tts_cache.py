import hashlib
import os


class TTSCache:
    """Cache file TTS để tránh gọi API trùng lặp"""

    def __init__(self, cache_dir="tts_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _make_key(self, text, voice, rate):
        raw = f"{text}|{voice}|{rate}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get_path(self, text, voice, rate):
        key = self._make_key(text, voice, rate)
        path = os.path.join(self.cache_dir, f"{key}.mp3")
        return path if os.path.exists(path) else None

    def save(self, text, voice, rate, audio_path):
        key = self._make_key(text, voice, rate)
        dest = os.path.join(self.cache_dir, f"{key}.mp3")
        if not os.path.exists(dest):
            os.rename(audio_path, dest)
        return dest


# Singleton
_cache = None


def get_cache():
    global _cache
    if _cache is None:
        _cache = TTSCache()
    return _cache