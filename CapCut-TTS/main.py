import requests
import json
import time

# ======================== HARDCODE LOGIN ========================
CAPCUT_EMAIL = "favonian253@lovexq.online"
CAPCUT_PASSWORD = "@k47ForEveryChinese"
# ================================================================

class CapCutTTS:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "Accept-Language": "vi-VN",
            "Origin": "https://www.capcut.com",
            "Referer": "https://www.capcut.com/",
            "Content-Type": "application/json"
        }

    def login(self):
        url = "https://login-row.www.capcut.com/passport/web/email/login/"
        payload = {"email": CAPCUT_EMAIL, "password": CAPCUT_PASSWORD}
        print(f"[*] Đang login...")
        res = self.session.post(url, json=payload, headers=self.headers)
        return res.status_code == 200 and "sessionid" in self.session.cookies

    def get_dynamic_audio_link(self, text):
        """
        Đây là bước để link KHÔNG BỊ CHẾT. 
        Nó gọi API tts/create để server trả về link mới dựa trên text.
        """
        url = "https://edit-api-sg.capcut.com/lv/v1/tts/create"
        payload = {
            "text": text,
            "speaker_id": "21703", # Giọng nữ VN
            "speed": 1.0,
            "pitch": 1.0,
            "volume": 1.0
        }
        print(f"[*] Đang gọi API tạo TTS cho nội dung: '{text}'...")
        res = self.session.post(url, json=payload, headers=self.headers)
        res_json = res.json()
        
        # Trích xuất link động từ data trả về
        return res_json.get("data", {}).get("audio_url")

    def download_audio(self, dynamic_url):
        if not dynamic_url:
            print("[-] Lỗi: Không lấy được link audio động từ API.")
            return
            
        headers = {**self.headers, "Range": "bytes=0-"}
        print("[*] Đang tải audio từ link động vừa tạo...")
        res = self.session.get(dynamic_url, headers=headers)
        
        with open("output.mp3", "wb") as f:
            f.write(res.content)
        print("[+] Xong! File output.mp3 đã được cập nhật nội dung mới.")

if __name__ == "__main__":
    tts = CapCutTTS()
    if tts.login():
        # Ông đổi text ở đây, link tải về sẽ tự động đổi theo, không bị chết link cũ
        noidung = "xin chào ông chủ" 
        
        # Bước này thay thế cho việc dán link AUDIO_LINK thủ công
        link_moi = tts.get_dynamic_audio_link(noidung)
        
        # Tải link mới đó về
        tts.download_audio(link_moi)
