import os
from google.cloud import texttospeech_v1beta1 as texttospeech

KEY_PATH = "service-account.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_PATH

def list_vietnamese_voices():
    client = texttospeech.TextToSpeechClient()
    # Lấy danh sách giọng nói
    response = client.list_voices(language_code="vi-VN")
    
    print(f"{'Voice ID':<30} | {'SSML Gender':<15} | {'Natural Sample Rate'}")
    print("-" * 70)
    
    for voice in response.voices:
        # Lọc để xem các mô hình rẻ hơn Chirp (thường không có chữ 'Chirp' trong tên)
        name = voice.name
        gender = texttospeech.SsmlVoiceGender(voice.ssml_gender).name
        rate = voice.natural_sample_rate_hertz
        print(f"{name:<30} | {gender:<15} | {rate}Hz")

if __name__ == "__main__":
    list_vietnamese_voices()
