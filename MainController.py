import os
import shutil
import subprocess
import signal
import sys
import json
import re
import requests
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

from utils.task_lock import TaskLock
from utils.task_progress import (
    atomic_write_json,
    empty_progress,
    fingerprint_matches,
    load_progress,
    mark_done,
    progress_path,
    reset_from,
    save_progress,
    source_identity,
    stage_done,
)


TIMESTAMP_LINE_RE = re.compile(r"^\[\d{2}:\d{2}:\d{2},\d{3}\]\s+\S")


class MainController:
    def __init__(self):
        self.children = []
        signal.signal(signal.SIGINT, self._terminate_all_children)
        signal.signal(signal.SIGTERM, self._terminate_all_children)

        try:
            from TokenManager import TokenManager
            self.TM = TokenManager()
        except ImportError:
            self.TM = None

        self.BaseDir = os.path.dirname(os.path.abspath(__file__))
        self.OutputDir = os.path.join(self.BaseDir, "final_output")
        os.makedirs(self.OutputDir, exist_ok=True)

    def terminate_children(self):
        """Kill các process con đang chạy (dùng khi đóng app hoặc nhận signal)."""
        for proc in list(self.children):
            if proc.poll() is None:
                try:
                    if sys.platform == "win32":
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
                    else:
                        pgid = os.getpgid(proc.pid)
                        os.killpg(pgid, signal.SIGKILL)
                except Exception:
                    pass
        self.children.clear()

    def _terminate_all_children(self, signum=None, frame=None):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        print("\n[HETHONG] Dung tat ca tien trinh...")
        self.terminate_children()
        print("[HETHONG] Da quet sach. Thoat.")
        os._exit(1)

    def _run_process(self, command):
        kwargs = {}
        if sys.platform != "win32":
            kwargs.update(preexec_fn=os.setsid)
        if command[0] == "python":
            command.insert(1, "-u")
        proc = subprocess.Popen(command, **kwargs)
        self.children.append(proc)
        try:
            return_code = proc.wait()
        finally:
            if proc in self.children:
                self.children.remove(proc)
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, command)
        return return_code

    def _run_shared_stt(self, input_path, output_path, device, language, model_size, num_workers):
        """Chạy STT trong process chính để các thread dùng chung một WhisperModel."""
        from stt import process_video

        success = process_video(
            input_path,
            output_path,
            device=device,
            language=language,
            model_size=model_size,
            num_workers=num_workers,
        )
        if not success:
            raise RuntimeError(f"Whisper STT thất bại: {input_path}")

    # === J2DOWNLOAD ===
    def _get_j2download_site(self, url):
        """Xac dinh site j2download dua tren loai URL"""
        if "douyin.com" in url or "tiktok.com" in url:
            return "https://j2download.com"
        elif "facebook.com" in url or "fb.watch" in url or "fb.com" in url:
            return "https://j2download.com/facebook"
        elif "youtube.com" in url or "youtu.be" in url:
            return "https://j2download.com/youtube"
        else:
            return "https://j2download.com"

    def _download_via_j2download(self, url, output_path, j2_site):
        """Tai video tu j2download bang Playwright."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = context.new_page()
                for attempt in range(10):
                    video_url = None
                    try:
                        page.goto(j2_site, wait_until="networkidle")
                        page.fill('input[id="url"]', url)
                        page.wait_for_timeout(500)
                        with page.expect_response("**/api/autolink", timeout=15000) as response_info:
                            page.click('button[type="submit"]')
                        video_data = response_info.value.json()
                        if not video_data.get("error"):
                            medias = video_data.get("medias", [])
                            target = next((m for m in medias if m.get("quality") == "HD No Watermark"),
                                          next((m for m in medias if m.get("quality") == "No Watermark"),
                                               next((m for m in medias if m.get("type") == "video"), None)))
                            if target:
                                video_url = target["url"]

                        if video_url:
                            with requests.get(video_url, stream=True, timeout=120) as response:
                                response.raise_for_status()
                                with open(output_path, "wb") as output_file:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        output_file.write(chunk)
                            if os.path.exists(output_path):
                                browser.close()
                                return True
                    except Exception as e:
                        print(f"J2 loi ({j2_site}, lan {attempt + 1}/10): {e}")
                browser.close()
        except Exception as e:
            print(f"Loi J2 Playwright: {e}")
        return False

    # === SEEKIN.AI CŨ (ĐÃ COMMENT, GIỮ LẠI ĐỂ THAM KHẢO) ===
    '''
    def _get_seekin_site(self, url):
        """Xac dinh site seekin.ai dua tren loai URL"""
        if "facebook.com" in url or "fb.watch" in url or "fb.com" in url:
            return "https://www.seekin.ai/facebook-video-downloader"
        elif "youtube.com" in url or "youtu.be" in url:
            return "https://www.seekin.ai/youtube-video-downloader"
        elif "douyin.com" in url:
            return "https://www.seekin.ai/douyin-downloader"
        elif "tiktok.com" in url:
            return "https://www.seekin.ai/download-tiktok-no-watermark"
        elif "instagram.com" in url:
            return "https://www.seekin.ai/download-instagram-reels"
        elif "twitter.com" in url or "x.com" in url:
            return "https://www.seekin.ai/twitter-video-downloader"
        else:
            return "https://www.seekin.ai/"

    def _download_via_seekin_playwright(self, url, output_path):
        """Dung Playwright de mo seekin.ai, dan link, bam nut, lay video_url tu response, tai bang requests"""
        seekin_site = self._get_seekin_site(url)
        for attempt in range(10):
            try:
                video_url = None
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    )
                    page = context.new_page()

                    # Lang nghe response tu API
                    def handle_response(response):
                        nonlocal video_url
                        if "api.seekin.ai/ikool/media/download" in response.url:
                            try:
                                data = response.json()
                                if data.get("code") == "0000":
                                    medias = data.get("data", {}).get("medias", [])
                                    if medias:
                                        # Chon chat luong tot nhat
                                        quality_order = ["8K", "4K", "2160p", "1080p", "720p", "540p", "480p", "360p"]
                                        selected = None
                                        for q in quality_order:
                                            selected = next((m for m in medias if q in (m.get("format") or "")), None)
                                            if selected:
                                                break
                                        if not selected:
                                            selected = next((m for m in medias if m.get("url")), None)
                                        if selected:
                                            video_url = selected["url"]
                                            format_label = selected.get("format", "unknown")
                                            print(f"Tim thay link: {format_label}")
                            except Exception:
                                pass

                    page.on("response", handle_response)

                    print(f"Dang mo {seekin_site} (lan {attempt + 1}/10)...")
                    page.goto(seekin_site, wait_until="networkidle")
                    page.wait_for_timeout(1000)

                    # Dan link URL vao input
                    print("Dang dan link...")
                    page.fill('input[placeholder*="Enter your link"], input[placeholder*="paste"], input[type="url"], input[id*="url"], input[name*="url"]', url)
                    page.wait_for_timeout(500)

                    # Bam nut download
                    print("Dang bam nut download...")
                    page.click('button[type="submit"], button:has-text("Download"), button:has-text("Get"), button:has-text("Start")')
                    page.wait_for_timeout(3000)

                    browser.close()

                # Neu co video_url, tai bang requests
                if video_url:
                    print(f"Dang tai video tu: {video_url[:80]}...")
                    with requests.get(video_url, stream=True, timeout=120) as r:
                        r.raise_for_status()
                        with open(output_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                    if os.path.exists(output_path):
                        return True

                print("Khong lay duoc link video tu seekin.ai")
                continue

            except Exception as e:
                print(f"Loi seekin Playwright (lan {attempt + 1}): {e}")
                continue

        return False

    def _download_seekin(self, url, output_path):
        """Tai video bang seekin.ai - Playwright dan link bam nut, requests tai video"""
        return self._download_via_seekin_playwright(url, output_path)
    '''

    def DownloadVideo(self, url, output_path):
        print(f"Dang tai video tu: {url}")
        # Tải vào file tạm; chỉ thay file chính khi video đã đọc được.
        tmp_path = output_path + ".part.mp4"
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        j2_site = self._get_j2download_site(url)
        ok = self._download_via_j2download(url, tmp_path, j2_site)
        if not ok or not self._video_ready(tmp_path):
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return False
        os.replace(tmp_path, output_path)
        return True

    def CheckGoogleToken(self):
        key_path = os.path.join(self.BaseDir, "service-account.json")
        if not os.path.exists(key_path):
            raise Exception("Thieu file 'service-account.json'.")
        return True

    @staticmethod
    def _file_ready(path, min_size=1):
        try:
            return os.path.isfile(path) and os.path.getsize(path) >= min_size
        except OSError:
            return False

    @staticmethod
    def _video_ready(path):
        """Chỉ resume video khi ffprobe đọc được và thời lượng lớn hơn 0."""
        if not MainController._file_ready(path, 1024):
            return False
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", path,
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
            return float(result.stdout.strip()) > 0
        except (OSError, ValueError, subprocess.SubprocessError):
            return False

    @staticmethod
    def _text_ready(path):
        """File phụ đề/STT hợp lệ: có dòng và mọi dòng đúng [hh:mm:ss,mmm]."""
        try:
            if not MainController._file_ready(path):
                return False
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            return bool(lines) and all(TIMESTAMP_LINE_RE.match(line) for line in lines)
        except (OSError, UnicodeDecodeError):
            return False

    def _final_output_done(self, path, config_fp, source=None):
        """Output cuối đã xong chưa. Có meta thì phải khớp config + nguồn hiện tại."""
        if not self._video_ready(path):
            return False
        meta_path = path + ".meta.json"
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, ValueError):
            # Output từ bản cũ chưa có meta: coi như đã xong.
            return True
        if config_fp and meta.get("config_fingerprint") != config_fp:
            return False
        old_source = meta.get("source") or {}
        if source and old_source and old_source != source:
            return False
        return True

    @staticmethod
    def _write_final_meta(path, task_id, config_fp, source):
        atomic_write_json(path + ".meta.json", {
            "version": 1,
            "task_id": task_id,
            "config_fingerprint": config_fp,
            "source": source,
            "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        })

    # File cần xoá khi phải làm lại một stage.
    STAGE_ARTIFACTS = {
        "stt": ["stt_raw.txt", "stt_raw.txt.part"],
        "translate": [
            "translated.txt", "translated.txt.tmp",
            "filtered.txt", "filtered.txt.tmp", "filtered.txt.progress.json",
        ],
        "filter": ["filtered.txt", "filtered.txt.tmp"],
        "preprocess": [
            "preprocessed_video.mp4", "cleaned_video.mp4", "cleaned_video.part.mp4",
        ],
        "png_overlay": ["overlayed_video.mp4", "overlayed_video.mp4.part.mp4"],
        "render": [
            "subbed_temp.mp4", "subbed_temp.mp4.part.mp4",
            "rvc_internal_result.mp4", "combined_voice_final.wav",
            "final_sub_generated.ass", "ffmpeg_filter_script.txt",
            "raw_tmp_audio", "rvc_tmp_audio",
        ],
    }

    def _delete_stage_artifacts(self, task_dir, stages):
        for stage in stages:
            for name in self.STAGE_ARTIFACTS.get(stage, []):
                path = os.path.join(task_dir, name)
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    elif os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass

    def _stage_ready(self, progress, stage, task_dir, path, validator):
        """True nếu stage đã xong và artifact còn tốt.

        Nếu progress nói xong nhưng file hỏng/mất -> reset stage + phụ thuộc.
        Nếu file tốt nhưng progress chưa kịp ghi (mất điện sau replace) -> mark done.
        """
        if stage_done(progress, stage):
            if validator(path):
                return True
            print(f"[RESUME] Stage {stage}: artifact hong/mat -> lam lai stage + phu thuoc.")
            reset = reset_from(progress, stage)
            self._delete_stage_artifacts(task_dir, reset)
            save_progress(task_dir, progress)
            return False

        if validator(path):
            mark_done(progress, stage)
            save_progress(task_dir, progress)
            print(f"[RESUME] Stage {stage}: file da xong, cap nhat progress.")
            return True
        return False

    @staticmethod
    def _reload_progress(task_dir, fallback):
        """Subprocess có thể đã cập nhật progress.json -> đọc lại trước khi ghi."""
        return load_progress(task_dir) or fallback

    def ExecuteWorkflow(self, *args, **kwargs):
        """Bọc lock theo task để 2 instance app không cùng ghi một TaskDir."""
        task_id = kwargs.get("TaskId")
        if task_id is None and len(args) > 7:
            task_id = args[7]
        if not task_id:
            return self._execute_workflow_inner(*args, **kwargs)

        lock_path = os.path.join(self.BaseDir, "Tasks", ".locks", f"task_{task_id}.lock")
        lock = TaskLock(lock_path)
        if not lock.acquire():
            print(f"[{task_id}] Task dang duoc xu ly boi tien trinh khac -> bo qua.")
            return None
        try:
            return self._execute_workflow_inner(*args, **kwargs)
        finally:
            lock.release()

    def _execute_workflow_inner(self, VideoUrl, VoiceType, RvcModel, AudioMode, BlurSub, BgmFile, MoodStyle, TaskId,
                        TransEngine="FILTER", Speed=1.0, Fps=30, F0Key=0, SttDevice="cuda", RvcDevice="cuda",
                        RvcBase="EDGE", SourceLang="zh", VoiceRate=1.5, GttsRate=1.5, DVoiceRate=1.1, EdgeRate="+25%",
                        NeutralVoiceId="vi-VN-Wavenet-C", EdgeVoiceId="vi-VN-HoaiMyNeural",
                        SttModel="small", Quality="medium", RenderDevice="auto", RvcMode="docker",
                        SubtitlePosition="duoi_giua", FontSize=32, MarginV=40,
                        BlurStartPercent=80, BlurEndPercent=95, BlurIntensity=10,
                        AspectRatio="auto", FontName="Arial",
                        FontColor="#FFFF00", OutlineColor="#000000", BackColor="#80000000",
                        SubBackground=True,
                        TikTokVoice="cutefemale",
                        Brightness=0, CutStart=0, CutEnd=0,
                        EnablePngOverlay=False, PngPath=None, PngPosX=50, PngPosY=10, PngAnchor="center",
                        PngWidthPercent=40, PngStartTime=0, PngEndTime=0, PngFullVideo=False,
                        HasSubtitle=True, SttWorkers=1, ConfigFingerprint=None):

        TaskDir = os.path.join(self.BaseDir, "Tasks", f"Task_{TaskId}")
        os.makedirs(TaskDir, exist_ok=True)

        SourceVideo = os.path.join(TaskDir, "source_video.mp4")
        OriginalVideo = os.path.join(TaskDir, "original_video.mp4")
        CleanedVideo = os.path.join(TaskDir, "cleaned_video.mp4")
        PreprocessedVideo = os.path.join(TaskDir, "preprocessed_video.mp4")
        OverlayedVideo = os.path.join(TaskDir, "overlayed_video.mp4")
        SttPath = os.path.join(TaskDir, "stt_raw.txt")
        TransPath = os.path.join(TaskDir, "translated.txt")
        FilteredPath = os.path.join(TaskDir, "filtered.txt")
        SubbedTemp = os.path.join(TaskDir, "subbed_temp.mp4")
        FinalOutput = os.path.join(self.OutputDir, f"Reup_{TaskId}.mp4")
        ProgressPath = progress_path(TaskDir)

        if os.path.exists(SourceVideo):
            source_for_fp = SourceVideo
        elif not VideoUrl.startswith(("http://", "https://")) and os.path.exists(VideoUrl):
            source_for_fp = VideoUrl
        else:
            source_for_fp = None
        source_id = source_identity(source_for_fp) if source_for_fp else {}
        config_fp = ConfigFingerprint or ""

        try:
            if self._final_output_done(FinalOutput, config_fp, source_id):
                print(f"[{TaskId}] RESUME: final output da hoan tat.")
                shutil.rmtree(TaskDir)
                return FinalOutput

            progress = load_progress(TaskDir)
            if progress is None:
                # TaskDir từ bản cũ (chưa có progress.json): KHÔNG xoá, để các
                # stage bên dưới tự nhận artifact hợp lệ qua _stage_ready().
                progress = empty_progress(TaskId, config_fp, source_id)
                save_progress(TaskDir, progress)
            elif not fingerprint_matches(progress, config_fp, source_id):
                print(f"[{TaskId}] Fingerprint thay doi -> xu ly lai task tu dau.")
                shutil.rmtree(TaskDir)
                os.makedirs(TaskDir, exist_ok=True)
                progress = empty_progress(TaskId, config_fp, source_id)
                save_progress(TaskDir, progress)

            # Có thể app đã dừng sau khi render xong nhưng trước khi move file.
            # subbed_temp hợp lệ chính là tài nguyên cuối nên không cần chạy lại
            # bất kỳ bước nào phía trước.
            if self._video_ready(SubbedTemp):
                print(f"[{TaskId}] RESUME B4: thu hoi video render da hoan tat.")
                if os.path.exists(FinalOutput):
                    os.remove(FinalOutput)
                os.replace(SubbedTemp, FinalOutput)
                self._write_final_meta(FinalOutput, TaskId, config_fp, source_id)
                if not self._video_ready(FinalOutput):
                    raise Exception("Video render da thu hoi nhung khong hop le.")
                shutil.rmtree(TaskDir)
                return FinalOutput

            # --- INPUT ---
            if self._video_ready(SourceVideo):
                print(f"[{TaskId}] RESUME INPUT: dung source_video.mp4 da co.")
            else:
                while True:
                    if os.path.exists(VideoUrl):
                        tmp_source = SourceVideo + ".part.mp4"
                        shutil.copy2(VideoUrl, tmp_source)
                        if not self._video_ready(tmp_source):
                            try:
                                os.remove(tmp_source)
                            except OSError:
                                pass
                            raise Exception("Video nguon copy khong hop le.")
                        os.replace(tmp_source, SourceVideo)
                        break
                    if VideoUrl.startswith(("http://", "https://")):
                        if self.DownloadVideo(VideoUrl, SourceVideo):
                            break
                        print(f"[{TaskId}] Tai that bai. Lap lai...")
                        continue
                    raise Exception("Duong dan video khong hop le.")
                if not self._video_ready(SourceVideo):
                    raise Exception("Video dau vao khong hop le hoac chua tai xong.")

            # Ghi lại danh tính nguồn thật (lần đầu có thể chưa có SourceVideo).
            source_id = source_identity(SourceVideo)
            progress.setdefault("fingerprint", {})["source"] = source_id
            save_progress(TaskDir, progress)

            # --- B1: STT ---
            if self._stage_ready(progress, "stt", TaskDir, SttPath, self._text_ready):
                print(f"[{TaskId}] RESUME B1: bo qua STT, da co stt_raw.txt.")
            else:
                print(f"[{TaskId}] STT (Device: {SttDevice}, Model: {SttModel}, Lang: {SourceLang})...")
                self._run_shared_stt(
                    SourceVideo,
                    SttPath,
                    device=SttDevice,
                    language=SourceLang,
                    model_size=SttModel,
                    num_workers=SttWorkers,
                )
                if not self._text_ready(SttPath):
                    raise Exception("STT khong tao duoc stt_raw.txt hop le.")
                with open(SttPath, "r", encoding="utf-8") as f:
                    line_count = sum(1 for line in f if line.strip())
                mark_done(progress, "stt", file="stt_raw.txt", lines=line_count)
                save_progress(TaskDir, progress)

            # --- B2: Dich & Filter ---
            if TransEngine == "GEMINI":
                if self._stage_ready(progress, "translate", TaskDir, FilteredPath, self._text_ready):
                    print(f"[{TaskId}] RESUME B2: bo qua Gemini + Filter.")
                else:
                    print(f"[{TaskId}] Gemini + Filter...")
                    self._run_process(["python", "gemini_trans.py", "--input", SttPath,
                                       "--output", FilteredPath, "--mood", MoodStyle, "--lang", SourceLang,
                                       "--progress", ProgressPath])
                    if not self._text_ready(FilteredPath):
                        raise Exception("Gemini khong tao duoc filtered.txt hop le.")
                    progress = self._reload_progress(TaskDir, progress)
                    mark_done(progress, "translate", mode="GEMINI", output="filtered.txt")
                    mark_done(progress, "filter", skipped=False)
                    save_progress(TaskDir, progress)
                if not stage_done(progress, "filter"):
                    mark_done(progress, "filter", skipped=False)
                    save_progress(TaskDir, progress)
                SubToRender = FilteredPath
            else:
                if self._stage_ready(progress, "translate", TaskDir, TransPath, self._file_ready):
                    print(f"[{TaskId}] RESUME B2a: bo qua dich, da co translated.txt.")
                else:
                    print(f"[{TaskId}] Dich phu de...")
                    self.HandleSmartTranslation(SttPath, TransPath, TaskId)
                    if not self._file_ready(TransPath):
                        raise Exception("Dich khong tao duoc translated.txt.")
                    progress = self._reload_progress(TaskDir, progress)
                    mark_done(progress, "translate", mode="FILTER", output="translated.txt")
                    save_progress(TaskDir, progress)

                if self._stage_ready(progress, "filter", TaskDir, FilteredPath, self._text_ready):
                    print(f"[{TaskId}] RESUME B2b: bo qua filter.")
                else:
                    print(f"[{TaskId}] Filter phu de...")
                    self._run_process(["python", "filter.py", "--input", TransPath,
                                       "--output", FilteredPath, "--mood", MoodStyle])
                    if self._text_ready(FilteredPath):
                        progress = self._reload_progress(TaskDir, progress)
                        mark_done(progress, "filter", skipped=False)
                        save_progress(TaskDir, progress)
                if self._file_ready(FilteredPath, 11):
                    SubToRender = FilteredPath
                else:
                    SubToRender = TransPath

            # --- B3: Preprocess ---
            if self._stage_ready(progress, "preprocess", TaskDir, PreprocessedVideo, self._video_ready):
                print(f"[{TaskId}] RESUME B3: bo qua preprocess.")
            else:
                if self._video_ready(CleanedVideo):
                    print(f"[{TaskId}] RESUME B3: thu hoi cleaned_video.mp4 da hoan tat.")
                    os.replace(CleanedVideo, PreprocessedVideo)
                else:
                    shutil.copy2(SourceVideo, OriginalVideo)
                    print(
                        f"[{TaskId}] Preprocess "
                        f"(Speed: {Speed}x, Quality: {Quality}, Device: {RenderDevice})..."
                    )
                    pre_cmd = [
                        "python", "pre_process_video.py",
                        "--task_dir", TaskDir, "--mode", AudioMode.lower(),
                        "--speed", str(Speed), "--fps", str(Fps),
                        "--quality", Quality, "--device", RenderDevice,
                        "--brightness", str(Brightness),
                        "--cut_start", str(CutStart),
                        "--cut_end", str(CutEnd)
                    ]
                    if BgmFile:
                        pre_cmd.extend(["--bgm", BgmFile])
                    self._run_process(pre_cmd)
                    if not self._video_ready(CleanedVideo):
                        raise Exception("Preprocess khong tao duoc video hop le.")
                    os.replace(CleanedVideo, PreprocessedVideo)
                if not self._video_ready(PreprocessedVideo):
                    raise Exception("Preprocess khong tao duoc video hop le.")
                mark_done(progress, "preprocess", file="preprocessed_video.mp4")
                save_progress(TaskDir, progress)

            shutil.copy2(PreprocessedVideo, OriginalVideo)

            # --- B3.5: PNG Overlay ---
            if EnablePngOverlay and PngPath and os.path.exists(PngPath):
                if self._stage_ready(progress, "png_overlay", TaskDir, OverlayedVideo, self._video_ready):
                    print(f"[{TaskId}] RESUME B3.5: bo qua PNG overlay.")
                else:
                    print(f"[{TaskId}] Chen PNG overlay...")
                    overlay_cmd = [
                        "python", "subVideo_png_overlay.py",
                        "--input", PreprocessedVideo, "--output", OverlayedVideo,
                        "--png", PngPath,
                        "--pos_x", str(PngPosX), "--pos_y", str(PngPosY),
                        "--anchor", PngAnchor, "--width_percent", str(PngWidthPercent),
                        "--start_time", str(PngStartTime), "--end_time", str(PngEndTime)
                    ]
                    if PngFullVideo:
                        overlay_cmd.append("--full_video")
                    self._run_process(overlay_cmd)
                    if not self._video_ready(OverlayedVideo):
                        raise Exception("PNG overlay khong tao duoc video hop le.")
                    mark_done(progress, "png_overlay", file="overlayed_video.mp4")
                    save_progress(TaskDir, progress)
                shutil.copy2(OverlayedVideo, OriginalVideo)
            else:
                if not stage_done(progress, "png_overlay"):
                    mark_done(progress, "png_overlay", skipped=True)
                    save_progress(TaskDir, progress)

            # --- B4: Render ---
            if VoiceType == "VIENEU":
                script_render = "subVideo_vietNeu.py"
            elif VoiceType == "RVC":
                script_render = "subVideo_rvc.py"
            else:
                script_render = "subVideo_gg.py"

            if self._stage_ready(progress, "render", TaskDir, SubbedTemp, self._video_ready):
                print(f"[{TaskId}] RESUME B4: bo qua render, video da hoan tat.")
            else:
                if VoiceType == "GTTS" or (VoiceType == "RVC" and RvcBase == "NEUTRAL"):
                    self.CheckGoogleToken()
                print(f"[{TaskId}] Render video...")
                render_cmd = [
                    "python", script_render,
                    "--task_dir", TaskDir, "--sub", SubToRender,
                    "--output", SubbedTemp, "--speed", str(Speed),
                    "--progress", ProgressPath,
                    "--tts_engine", VoiceType, "--f0_key", str(F0Key),
                    "--voice_rate", str(VoiceRate), "--gtts_rate", str(GttsRate),
                    "--dvoice_rate", str(DVoiceRate), "--edge_rate", str(EdgeRate),
                    "--neutral_voice", NeutralVoiceId, "--edge_voice", EdgeVoiceId,
                    "--quality", Quality, "--device", RenderDevice,
                    "--subtitle_position", SubtitlePosition,
                    "--font_size", str(FontSize), "--margin_v", str(MarginV),
                    "--blur_start_percent", str(BlurStartPercent), "--blur_end_percent", str(BlurEndPercent),
                    "--blur_intensity", str(BlurIntensity),
                    "--aspect_ratio", AspectRatio, "--font_name", FontName,
                    "--font_color", FontColor, "--outline_color", OutlineColor,
                    "--back_color", BackColor,
                    "--sub_background", str(SubBackground),
                    "--tiktok_voice", TikTokVoice,
                    "--has_subtitle", str(HasSubtitle)
                ]

                if VoiceType == "RVC":
                    render_cmd.extend(["--model", RvcModel, "--device", RvcDevice,
                                       "--base_tts", RvcBase, "--rvc_mode", RvcMode,
                                       "--render_device", RenderDevice])
                    render_cmd.extend(["--subtitle_position", SubtitlePosition,
                                       "--font_size", str(FontSize), "--margin_v", str(MarginV),
                                       "--blur_start_percent", str(BlurStartPercent), "--blur_end_percent", str(BlurEndPercent),
                                       "--blur_intensity", str(BlurIntensity),
                                       "--aspect_ratio", AspectRatio, "--font_name", FontName,
                                       "--font_color", FontColor, "--outline_color", OutlineColor,
                                       "--back_color", BackColor,
                                       "--sub_background", str(SubBackground),
                                       "--has_subtitle", str(HasSubtitle)])

                if BgmFile:
                    render_cmd.extend(["--bgm", BgmFile])
                if BlurSub:
                    render_cmd.append("--blur")

                self._run_process(render_cmd)
                if not self._video_ready(SubbedTemp):
                    raise Exception("Render khong tao duoc video hop le.")
                progress = self._reload_progress(TaskDir, progress)
                mark_done(progress, "render", output="subbed_temp.mp4")
                save_progress(TaskDir, progress)

            if os.path.exists(FinalOutput):
                os.remove(FinalOutput)
            os.replace(SubbedTemp, FinalOutput)
            if not self._video_ready(FinalOutput):
                raise Exception("Final output khong hop le.")
            self._write_final_meta(FinalOutput, TaskId, config_fp, source_id)

            print(f"[{TaskId}] THANH CONG. Don dep tai nguyen task...")
            shutil.rmtree(TaskDir)
            return FinalOutput

        except Exception as e:
            print(f"[{TaskId}] LOI HETHONG: {str(e)}")
            print(f"[{TaskId}] Giu lai tai nguyen de resume: {TaskDir}")
            return None

    def HandleSmartTranslation(self, InputPath, OutputPath, TaskId):
        Token = self.TM.GetValidToken() if self.TM else "YOUR_DEFAULT_TOKEN"
        FileSize = os.path.getsize(InputPath)
        script = "transfile.py" if FileSize > 50 * 1024 else "trans.py"
        self._run_process(["python", script, "--input", InputPath, "--token", Token, "--output", OutputPath])
