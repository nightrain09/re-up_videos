import asyncio
import os
from playwright.async_api import async_playwright

# Cấu hình
TARGET_URL = 'https://vietphrase.info/'
AUTH_CHECK_URL = 'https://vietphrase.info/check-auth'
OUTPUT_FILE = 'chinese_token_trans.txt'
ADDITIONAL_KEYS_LIMIT = 50  # Mục tiêu: Lấy THÊM đúng 50 key mới
MAX_CONCURRENT_WORKERS = 8   # Giảm nhẹ số luồng để tải tài nguyên cho ổn định

WINDOWS_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# Bộ nhớ để kiểm soát
existing_tokens = set()
new_tokens_collected = set()
lock = asyncio.Lock()

def load_existing_tokens():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

async def harvest_worker(worker_id, browser):
    global new_tokens_collected, existing_tokens
    
    while len(new_tokens_collected) < ADDITIONAL_KEYS_LIMIT:
        context = await browser.new_context(
            user_agent=WINDOWS_UA,
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        # Can thiệp Navigator để tàng hình trên Linux
        await page.add_init_script("""
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        token_this_turn = None
        async def handle_response(response):
            nonlocal token_this_turn
            if AUTH_CHECK_URL in response.url:
                try:
                    data = await response.json()
                    token_this_turn = data.get("bearerToken")
                except: pass

        page.on("response", handle_response)

        try:
            # Tải đầy đủ tài nguyên (không chặn route nữa)
            await page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
            
            # Đợi một chút để script auth của web hoàn tất
            await asyncio.sleep(3)

            if token_this_turn:
                async with lock:
                    # Kiểm tra xem token này đã từng có trong file hoặc vừa lấy chưa
                    if (token_this_turn not in existing_tokens and 
                        token_this_turn not in new_tokens_collected and 
                        len(new_tokens_collected) < ADDITIONAL_KEYS_LIMIT):
                        
                        new_tokens_collected.add(token_this_turn)
                        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                            f.write(token_this_turn + "\n")
                        
                        print(f"[Worker {worker_id}] +1 Key mới ({len(new_tokens_collected)}/{ADDITIONAL_KEYS_LIMIT})")
        
        except Exception as e:
            # print(f"[Worker {worker_id}] Lỗi kết nối, đang thử lại...")
            pass
        finally:
            await page.close()
            await context.close()
        
        await asyncio.sleep(1)

async def main():
    global existing_tokens
    existing_tokens = load_existing_tokens()
    
    print(f"[*] File hiện tại đang có {len(existing_tokens)} key.")
    print(f"[*] Đang tiến hành lấy THÊM {ADDITIONAL_KEYS_LIMIT} key mới...")

    async with async_playwright() as p:
        # Tải đủ tài nguyên tốn RAM hơn nên không nên để luồng quá cao
        browser = await p.chromium.launch(headless=True)
        
        workers = [harvest_worker(i, browser) for i in range(MAX_CONCURRENT_WORKERS)]
        await asyncio.gather(*workers)
        
        await browser.close()
        print(f"\n[Xong] Đã lấy thêm thành công {len(new_tokens_collected)} key.")
        print(f"[*] Tổng số key trong file hiện tại: {len(load_existing_tokens())}")

if __name__ == "__main__":
    asyncio.run(main())
