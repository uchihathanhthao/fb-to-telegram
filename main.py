import time
import requests
import random
import threading
from datetime import datetime
import pytz
from flask import Flask
from bs4 import BeautifulSoup

# ============================================================
# 🔐 TELEGRAM BOT TOKEN
# ============================================================

BOT_TOKEN = "8746522888:AAE1drDmhydNlZB5YAkO82_u8ZzNsmZ_LxY"

# ============================================================
# ⚙️ TELEGRAM CHAT ID
# ============================================================

CHAT_ID = "-1003910530474"

# ============================================================
# 📘 FACEBOOK PAGES
# ============================================================

PAGE_LIST = [
    "CLBHuuNghiVietLaoTDMU",
    "lyluantreTDMU",
    "dhtdm2009",
    "thefoundersclub2018",
    "thanhdoanthanhphohochiminh",
    "clbsv5tottdmu",
    "XungKichTDMU",
    "tuoitredhthudaumot",
    "tdmu.flc",
    "hsvdhtdm",
    "clbvhbctttdmu",
    "Youth.KTCN",
    "ClbKynangSupham",
    "clbsinhvienkhoinghiepTDMU",
    "61552398976258",
    "doanhoikhoasupham",
    "clbthanhnientinhnguyen.tdmu",
    "KyNangTDMU",
    "FFL.TDMU",
    "khoangoaingu.tdmu",
    "100076805206008"
]

# Trỏ trực tiếp tới link mobile facebook của từng page
RSS_FEEDS = {
    page: f"https://m.facebook.com/{page}"
    for page in PAGE_LIST
}

# ============================================================
# 🧠 BỘ NHỚ BÀI ĐÃ GỬI
# ============================================================

sent_posts = set()
posts_lock = threading.Lock()

# ============================================================
# 💬 QUOTES (ĐÃ LƯỢC BỎ ICON VÀ TIÊU ĐỀ PHỤ)
# ============================================================

RAW_QUOTES = [
    "Nếu bạn dám thử thì tỉ lệ thành công là 50:50, còn nếu bạn đã chọn từ bỏ thì bạn chọn thất bại 100%.",
    "Nó không khó, nó chỉ mới thôi!",
    "Học nhanh có lợi hơn là học nhiều.",
    "Hệ thống quan trọng hơn nỗ lực.",
    "Trở thành thiên tài là điều có thể bắt chước được.",
    "FOCUS NOT BALANCE - Tập trung vào mục tiêu!",
    "Thời gian là hữu hạn, liệu ba mẹ bạn có thể đợi đến ngày bạn thành công?",
    "10 năm sau bạn sẽ là hình mẫu hay là nỗi nhục của chính bản thân năm 17 tuổi?",
    "Ước mơ chu du thế giới liệu có còn đó?",
    "Bạn chọn thức dậy và nỗ lực tới ước mơ hay ngủ và mơ tiếp giấc mơ đó?",
    "Ba mẹ, ông bà, người thân KHÔNG CHỜ BẠN ĐƯỢC ĐÂU!",
    "Vì một ngày có thể tự bỏ tiền đi du lịch thế giới CÙNG GIA ĐÌNH!",
    "HÃY TRỞ THÀNH NGƯỜI ĐẦU TIÊN TRONG GIA ĐÌNH ĐẶT CHÂN ĐẾN ĐẤT NƯỚC KHÁC!",
    "Đừng chùn bước, chúng ta đã đi một đoạn rất xa rồi.",
    "Cố chút nữa thôi! Bạn đã tốt hơn bạn của hôm qua rồi!",
    "Cuộc đua này không có người giỏi nhất, chỉ có người kiên trì nhất."
]

quote_queue = []
quote_lock = threading.Lock()

def get_next_quote():
    global quote_queue
    with quote_lock:
        if not quote_queue:
            quote_queue = RAW_QUOTES.copy()
            random.shuffle(quote_queue)
        return quote_queue.pop(0)

# ============================================================
# 📤 GỬI TELEGRAM
# ============================================================

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        print(f"Telegram HTTP {response.status_code}: {response.text[:500]}")
        return response.ok
    except Exception as error:
        print(f"❌ Lỗi kết nối Telegram: {error}")
        return False

def send_facebook_post(page_name, title, link):
    if not title:
        title = "Bài viết mới"
    message = (
        f"📢 **BÀI VIẾT MỚI**\n\n"
        f"📄 **Page:** {page_name}\n\n"
        f"{title}\n\n"
        f"🔗 [Xem bài viết]({link})"
    )
    success = send_telegram(message)
    if success:
        print(f"✅ ĐÃ GỬI | {page_name} | {title}")
    else:
        print(f"❌ GỬI THẤT BẠI | {page_name} | {title}")
    return success

# ============================================================
# 🔎 CÀO TRỰC TIẾP QUA PROXY GATEWAY AN TOÀN
# ============================================================

def read_page_feed(page_name, target_url):
    try:
        print(f"🔎 Đang quét page: {page_name}")
        
        proxied_url = f"https://api.allorigins.win/raw?url={requests.utils.quote(target_url)}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(proxied_url, headers=headers, timeout=20)
        if not response.ok:
            print(f"   ⚠️ Không thể kết nối tới {page_name} (HTTP {response.status_code})")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        entries = []
        
        posts = soup.find_all(['article', 'div'], class_ = lambda x: x and ('story' in x.lower() or 'post' in x.lower()))
        if not posts:
            posts = soup.find_all('div', style=True) or soup.find_all('p')

        for item in posts[:10]:
            text_content = item.get_text(separator=" ", strip=True)
            if len(text_content) > 30:
                link_tag = item.find('a', href=True)
                if link_tag and ('/posts/' in link_tag['href'] or '/photos/' in link_tag['href'] or 'story.php' in link_tag['href']):
                    post_link = f"https://facebook.com{link_tag['href']}" if link_tag['href'].startswith('/') else link_tag['href']
                else:
                    post_link = f"https://facebook.com/{page_name}"
                
                class DummyEntry:
                    pass
                entry = DummyEntry()
                entry.id = post_link
                entry.title = text_content[:200] + "..."
                entry.link = post_link
                
                if not any(e.link == post_link for e in entries):
                    entries.append(entry)

        print(f"   → {page_name}: tìm thấy {len(entries)} bài")
        return entries
    except Exception as error:
        print(f"❌ Lỗi quét {page_name}: {error}")
        return []

def get_post_id(entry):
    if getattr(entry, "id", None):
        return str(entry.id)
    if getattr(entry, "link", None):
        return str(entry.link)
    return None

# ============================================================
# 🆕 QUÉT FACEBOOK
# ============================================================

def check_facebook():
    first_run = True
    print("=" * 60)
    print("🚀 FACEBOOK SCRAPER BOT KHỞI ĐỘNG")
    print(f"📌 Số Page: {len(PAGE_LIST)}")
    print("⏱️ Chu kỳ quét: 5 phút")
    print("=" * 60)

    while True:
        cycle_start = time.time()
        for page_name, feed_url in RSS_FEEDS.items():
            entries = read_page_feed(page_name, feed_url)
            if not entries:
                continue
            for entry in reversed(entries):
                post_id = get_post_id(entry)
                if not post_id:
                    continue
                title = getattr(entry, "title", "Bài viết mới")
                link = getattr(entry, "link", "")
                if not link:
                    continue

                if first_run:
                    with posts_lock:
                        sent_posts.add(post_id)
                    continue

                with posts_lock:
                    if post_id in sent_posts:
                        continue
                    sent_posts.add(post_id)

                success = send_facebook_post(page_name, title, link)
                if not success:
                    with posts_lock:
                        sent_posts.discard(post_id)

        if first_run:
            first_run = False
            print(f"\n✅ ĐÃ HOÀN TẤT KHỞI TẠO. Đã ghi nhận {len(sent_posts)} bài cũ.")

        elapsed = time.time() - cycle_start
        print(f"\n⏱️ Chu kỳ hoàn tất sau {elapsed:.1f} giây. Nghỉ 5 phút...")
        time.sleep(300)

# ============================================================
# ⏰ HỆ THỐNG QUOTE
# ============================================================

def check_quotes():
    timezone = pytz.timezone("Asia/Ho_Chi_Minh")
    sent_slots = set()
    print("💬 Hệ thống Quote đã khởi chạy.")

    while True:
        try:
            now = datetime.now(timezone)
            slot = None
            if now.hour == 5 and now.minute == 0:
                slot = "05:00"
            elif now.hour == 13 and now.minute == 0:
                slot = "13:00"
            elif now.hour == 22 and now.minute == 0:
                slot = "22:00"

            if slot and slot not in sent_slots:
                quote = get_next_quote()
                print(f"💬 Đang gửi quote {slot}...")
                success = send_telegram(quote)
                if success:
                    sent_slots.add(slot)
                time.sleep(60)

            if now.hour == 0 and now.minute == 1:
                sent_slots.clear()
                print("🔄 Đã reset lịch quote cho ngày mới.")
                time.sleep(60)

            time.sleep(20)
        except Exception as error:
            print(f"❌ Lỗi hệ thống quote: {error}")
            time.sleep(30)

# ============================================================
# 🌐 FLASK WEB SERVER
# ============================================================

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Facebook Scraper Bot đang chạy 24/7."

@app.route("/test")
def test_send():
    success = send_telegram("🧪 **TEST TELEGRAM BOT**\n\nKết nối thành công!")
    return "✅ TEST THÀNH CÔNG!" if success else "❌ TEST THẤT BẠI!"

@app.route("/health")
def health():
    return "OK", 200

# ============================================================
# 🧪 LỆNH TEST QUOTE VÀ TEST POST GẦN NHẤT
# ============================================================

@app.route("/testquote")
def test_quote():
    quote = get_next_quote()
    test_message = f"🧪 **[TEST QUOTE]**\n\n{quote}"
    success = send_telegram(test_message)
    if success:
        return "✅ Đã test gửi Quote thành công! Hãy kiểm tra Telegram."
    return "❌ Test gửi Quote thất bại!"

@app.route("/testpost")
def test_post():
    for page_name, feed_url in RSS_FEEDS.items():
        entries = read_page_feed(page_name, feed_url)
        if not entries:
            continue
        
        # Bốc ngay bài đăng gần nhất (phần tử đầu tiên) để test ngay lập tức
        entry = entries[0]
        title = getattr(entry, "title", "Bài viết mới")
        link = getattr(entry, "link", "")
        
        if not link:
            link = f"https://facebook.com/{page_name}"
            
        message = (
            f"🧪 **[TEST BÀI ĐĂNG GẦN NHẤT]**\n\n"
            f"📄 **Page:** {page_name}\n\n"
            f"{title}\n\n"
            f"🔗 [Xem bài viết]({link})"
        )
        
        success = send_telegram(message)
        if success:
            return f"✅ Đã test lấy thành công bài viết gần nhất từ page: <b>{page_name}</b>!"
        else:
            return f"❌ Lỗi khi gửi tin nhắn test về Telegram cho page: {page_name}"
            
    return "❌ Không thể cào được bài viết nào từ danh sách các page lúc này."

# ============================================================
# 🚀 KHỞI ĐỘNG THREADS KHI IMPORT HOẶC CHẠY
# ============================================================

def start_background_tasks():
    if not BOT_TOKEN or "phần này" in BOT_TOKEN:
        print("❌ CHƯA ĐIỀN BOT_TOKEN!")
        return

    fb_thread = threading.Thread(target=check_facebook, name="FacebookMonitor", daemon=True)
    fb_thread.start()

    q_thread = threading.Thread(target=check_quotes, name="QuoteScheduler", daemon=True)
    q_thread.start()

start_background_tasks()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
