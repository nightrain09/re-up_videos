import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# Đọc API keys từ .env
api_keys_str = os.getenv("GEMINI_API_KEYS", "")
api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]

# Đọc models từ .env
models_str = os.getenv("GEMINI_MODELS", "")
models = [m.strip() for m in models_str.split(",") if m.strip()]

if not api_keys or not models:
    print("⚠️ Thiếu GEMINI_API_KEYS hoặc GEMINI_MODELS trong file .env")

def check_v1beta():
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": "hi"}]}]}

    print(f"{'STT':<4} | {'KEY (4 cuối)':<12} | {'MODEL':<30} | {'STATUS'}")
    print("-" * 65)

    count = 1
    for key in api_keys:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=7)
                
                if response.status_code == 200:
                    status = "✅ OK"
                elif response.status_code == 429:
                    status = "❌ LIMIT (429)"
                elif response.status_code == 403:
                    status = "🚫 KEY DIE (403)"
                elif response.status_code == 404:
                    status = "❓ NOT FOUND (404)"
                else:
                    status = f"⚠️ ERR {response.status_code}"

                print(f"{count:<4} | {key[-4:]:>12} | {model:<30} | {status}")
                
            except Exception as e:
                print(f"{count:<4} | {key[-4:]:>12} | {model:<30} | 💥 {str(e)[:15]}")
            
            count += 1

if __name__ == "__main__":
    check_v1beta()
