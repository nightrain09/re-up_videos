import os
import shutil
import subprocess
import signal
import sys
import requests
import json
import time
import hashlib
from playwright.sync_api import sync_playwright


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

    def _terminate_all_children(self, signum=None, frame=None):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        print("\n[HETHONG] Dung tat ca tien trinh...")
        for proc in self.children:
            if proc.poll() is None:
                try:
                    if sys.platform == "win32":
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
                    else:
                        pgid = os.getpgid(proc.pid)
                        os.killpg(pgid, signal.SIGKILL)
                except Exception:
                    pass
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

    # === J2DOWNLOAD CŨ (ĐÃ COMMENT, GIỮ LẠI ĐỂ THAM KHẢO) ===
    # def _get_j2download_site(self, url):
    #     """Xac dinh site j2download dua tren loai URL"""
    #     if "douyin.com" in url or "tiktok.com" in url:
    #         return "https://j2download.com"
    #     elif "facebook.com" in url or "fb.watch" in url or "fb.com" in url:
    #         return "https://j2download.com/facebook"
    #     elif "youtube.com" in url or "youtu.be" in url:
    #         return "https://j2download.com/youtube"
    #     else:
    #         return "https://j2download.com"  # default
    #
    # def _download_via_j2download(self, url, output_path, j2_site):
    #     """Tai video tu j2download bang Playwright (ho tro Douyin, Facebook, YouTube)"""
    #     try:
    #         with sync_playwright() as p:
    #             browser = p.chromium.launch(headless=True)
    #             context = browser.new_context(
    #                 user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    #             )
    #             page = context.new_page()
    #             for attempt in range(10):
    #                 video_url = None
    #                 try:
    #                     page.goto(j2_site, wait_until="networkidle")
    #                     page.fill('input[id="url"]', url)
    #                     page.wait_for_timeout(500)
    #                     page.click('button[type="submit"]')
    #                     try:
    #                         with page.expect_response("**/api/autolink", timeout=15000) as response_info:
    #                             video_data = response_info.value.json()
    #                         if not video_data.get("error"):
    #                             medias = video_data.get("medias", [])
    #                             target = next((m for m in medias if m.get("quality") == "HD No Watermark"),
    #                                           next((m for m in medias if m.get("quality") == "No Watermark"),
    #                                                next((m for m in medias if m.get("type") == "video"), None)))
    #                             if target:
    #                                 video_url = target["url"]
    #                     except Exception:
    #                         print(f"J2 loi ({j2_site}), chuyen sang Savetik...")
    #
    #                     # Fallback: Savetik cho Douyin
    #                     if not video_url and "douyin" in url:
    #                         print("Dang thu Savetik.co...")
    #                         page.goto("https://savetik.co/en/douyin-downloader")
    #

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

    def DownloadVideo(self, url, output_path):
        print(f"Dang tai video tu: {url}")
        if os.path.exists(output_path):
            os.remove(output_path)

        # Tat ca deu dung seekin.ai de download, khong can yt-dlp nua
        return self._download_seekin(url, output_path)

    def CheckGoogleToken(self):
        key_path = os.path.join(self.BaseDir, "service-account.json")
        if not os.path.exists(key_path):
            raise Exception("Thieu file 'service-account.json'.")
        return True

    def ExecuteWorkflow(self, VideoUrl, VoiceType, RvcModel, AudioMode, BlurSub, BgmFile, MoodStyle, TaskId,
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
                        HasSubtitle=True):

        if VoiceType == "GTTS" or (VoiceType == "RVC" and RvcBase == "NEUTRAL"):
            self.CheckGoogleToken()

        TaskDir = os.path.join(self.BaseDir, "Tasks", f"Task_{TaskId}")

        while True:
            try:
                if os.path.exists(TaskDir):
                    shutil.rmtree(TaskDir)
                os.makedirs(TaskDir, exist_ok=True)

                OriginalVideo = os.path.join(TaskDir, "original_video.mp4")
                CleanedVideo = os.path.join(TaskDir, "cleaned_video.mp4")
                SttPath = os.path.join(TaskDir, "stt_raw.txt")
                TransPath = os.path.join(TaskDir, "translated.txt")
                FilteredPath = os.path.join(TaskDir, "filtered.txt")
                SubbedTemp = os.path.join(TaskDir, "subbed_temp.mp4")
                FinalOutput = os.path.join(self.OutputDir, f"Reup_{TaskId}.mp4")

                # --- INPUT ---
                if os.path.exists(VideoUrl):
                    shutil.copy(VideoUrl, OriginalVideo)
                elif VideoUrl.startswith(("http://", "https://")):
                    success = self.DownloadVideo(VideoUrl, OriginalVideo)
                    if not success:
                        print(f"[{TaskId}] Tai that bai. Lap lai...")
                        continue
                else:
                    raise Exception("Duong dan video khong hop le.")

                # --- B1: STT ---
                print(f"[{TaskId}] STT (Device: {SttDevice}, Model: {SttModel}, Lang: {SourceLang})...")
                self._run_process(["python", "stt.py", "--input", OriginalVideo, "--output", SttPath,
                                   "--device", SttDevice, "--lang", SourceLang, "--model", SttModel])

                # --- B2: Dich & Filter ---
                if TransEngine == "GEMINI":
                    print(f"[{TaskId}] Gemini + Filter...")
                    self._run_process(["python", "gemini_trans.py", "--input", SttPath,
                                       "--output", FilteredPath, "--mood", MoodStyle, "--lang", SourceLang])
                    SubToRender = FilteredPath
                else:
                    print(f"[{TaskId}] Filter: Dich + Filter...")
                    self.HandleSmartTranslation(SttPath, TransPath, TaskId)
                    if os.path.exists(FilteredPath):
                        os.remove(FilteredPath)
                    self._run_process(["python", "filter.py", "--input", TransPath,
                                       "--output", FilteredPath, "--mood", MoodStyle])
                    if os.path.exists(FilteredPath) and os.path.getsize(FilteredPath) > 10:
                        SubToRender = FilteredPath
                    else:
                        SubToRender = TransPath

                # --- B3: Preprocess ---
                print(f"[{TaskId}] Preprocess (Speed: {Speed}x, Quality: {Quality}, Device: {RenderDevice})...")
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

                if os.path.exists(CleanedVideo):
                    os.replace(CleanedVideo, OriginalVideo)

                # --- B3.5: PNG Overlay (áp dụng cho MỌI loại giọng, chạy trước khi render) ---
                if EnablePngOverlay and PngPath and os.path.exists(PngPath):
                    print(f"[{TaskId}] Chen PNG overlay...")
                    OverlayedVideo = os.path.join(TaskDir, "overlayed_video.mp4")
                    overlay_cmd = [
                        "python", "subVideo_png_overlay.py",
                        "--input", OriginalVideo, "--output", OverlayedVideo,
                        "--png", PngPath,
                        "--pos_x", str(PngPosX), "--pos_y", str(PngPosY),
                        "--anchor", PngAnchor, "--width_percent", str(PngWidthPercent),
                        "--start_time", str(PngStartTime), "--end_time", str(PngEndTime)
                    ]
                    if PngFullVideo:
                        overlay_cmd.append("--full_video")
                    self._run_process(overlay_cmd)
                    if os.path.exists(OverlayedVideo):
                        os.replace(OverlayedVideo, OriginalVideo)

                # --- B4: Render ---
                print(f"[{TaskId}] Render video...")
                if VoiceType == "VIENEU":
                    script_render = "subVideo_vietNeu.py"
                elif VoiceType == "RVC":
                    script_render = "subVideo_rvc.py"
                else:
                    script_render = "subVideo_gg.py"

                render_cmd = [
                    "python", script_render,
                    "--task_dir", TaskDir, "--sub", SubToRender,
                    "--output", SubbedTemp, "--speed", str(Speed),
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
                    # RVC needs these too for its own argparse
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

                if os.path.exists(SubbedTemp):
                    shutil.move(SubbedTemp, FinalOutput)

                if os.path.exists(FinalOutput):
                    print(f"[{TaskId}] THANH CONG. Don dep...")
                    shutil.rmtree(TaskDir)
                    return FinalOutput

            except Exception as e:
                print(f"[{TaskId}] LOI HETHONG: {str(e)}")
                return None

    def HandleSmartTranslation(self, InputPath, OutputPath, TaskId):
        Token = self.TM.GetValidToken() if self.TM else "YOUR_DEFAULT_TOKEN"
        FileSize = os.path.getsize(InputPath)
        script = "transfile.py" if FileSize > 50 * 1024 else "trans.py"
        self._run_process(["python", script, "--input", InputPath, "--token", Token, "--output", OutputPath])