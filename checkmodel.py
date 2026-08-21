import os
import json
import requests
from google.oauth2 import service_account
import google.auth.transport.requests

# --- CẤU HÌNH ---
KEY_PATH = "service-account.json"
LOCATION = "us-central1" # Thử đổi sang "asia-southeast1" nếu muốn check vùng khác

def get_vertex_info():
    try:
        with open(KEY_PATH, 'r') as f:
            info = json.load(f)
            project_id = info.get("project_id")
        
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        creds = service_account.Credentials.from_service_account_file(KEY_PATH, scopes=scopes)
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        return creds.token, project_id
    except Exception as e:
        print(f"❌ Lỗi đọc file hoặc Token: {e}")
        return None, None

def list_supported_models():
    token, project_id = get_vertex_info()
    if not token or not project_id:
        return

    # Endpoint lấy danh sách model từ Vertex AI
    url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{LOCATION}/publishers/google/models"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    print(f"--- ĐANG QUÉT MODEL KHẢ DỤNG CHO PROJECT: {project_id} ({LOCATION}) ---")
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            models_data = response.json()
            if 'models' in models_data:
                print(f"{'INDEX':<5} | {'MODEL ID'}")
                print("-" * 50)
                for i, model in enumerate(models_data['models']):
                    # Lấy phần ID cuối cùng của model
                    model_id = model['name'].split('/')[-1]
                    print(f"{i+1:<5} | {model_id}")
            else:
                print("⚠️ Không tìm thấy model nào được kích hoạt trong vùng này.")
        else:
            print(f"❌ Lỗi {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")

if __name__ == "__main__":
    list_supported_models()
