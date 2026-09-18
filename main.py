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
    "khoangoaingu.tdmu"
]

# Không cần dùng RSS trung gian nữa, lưu trực tiếp tên Page
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
# 💬 QUOTES
# ============================================================

RAW_QUOTES = [
    "🌅 **LỜI NHẮC BUỔI SÁNG**\n\n'Nếu bạn dám thử thì tỉ lệ thành công là 50:50, còn nếu bạn đã chọn từ bỏ thì bạn chọn thất bại 100%.'",
    "🔥 **BẮT ĐẦU NGÀY MỚI**\n\n'Nó không khó, nó chỉ mới thôi!'",
    "💡 **TƯ DUY ĐÚNG ĐẮN**\n\n'Học nhanh có lợi hơn là học nhiều.'",
    "⚙️ **TỐI ƯU HÓA**\n\n'Hệ thống quan trọng hơn nỗ lực.'",
    "🎯 **BỨC PHÁ BẢN THÂN**\n\n'Trở thành thiên tài là điều có thể *bắt chước được*.'",
    "⚡ **TẬP TRUNG CAO ĐỘ**\n\n'**FOCUS NOT BALANCE** - Tập trung vào mục tiêu!'",
    "⏳ **LỜI NHẮC THỜI GIAN**\n\n'Thời gian là hữu hạn, liệu ba mẹ bạn có thể đợi đến ngày bạn thành công?'",
    "🪞 **LỜI THỨC TỈNH**\n\n'10 năm sau bạn sẽ là hình mẫu hay là nỗi nhục của chính bản thân năm 17 tuổi?'",
    "🌍 **MỤC TIÊU LỚN**\n\n'Ước mơ chu du thế giới liệu có còn đó?'",
    "🔔 **BÁO THỨC BẢN THÂN**\n\n'Bạn chọn thức dậy và nỗ lực tới ước mơ hay ngủ và mơ tiếp giấc mơ đó?'",
    "🚨 **LỜI CẢNH BÁO**\n\n'Ba mẹ, ông bà, người thân **KHÔNG CHỜ BẠN ĐƯỢC ĐÂU!**'",
    "✈️ **ĐỘNG LỰC GIA ĐÌNH**\n\n'Vì một ngày có thể tự bỏ tiền đi du lịch thế giới CÙNG GIA ĐÌNH!'",
    "🚀 **MỤC TIÊU TIÊN PHONG**\n\n'**HÃY TRỞ THÀNH NGƯỜI ĐẦU TIÊN TRONG GIA ĐÌNH ĐẶT CHÂN ĐẾN ĐẤT NƯỚC KHÁC!**'",
    "🛡️ **KIÊN TRÌ**\n\n'Đừng chùn bước, chúng ta đã đi một đoạn rất xa rồi.'",
    "🌱 **MỖI NGÀY MỘT CHÚT**\n\n'Cố chút nữa thôi! Bạn đã tốt hơn bạn của hôm qua rồi!'",
    "🏆 **BẢN LĨNH**\n\n'Cuộc đua này không có người giỏi nhất, chỉ có người kiên trì nhất.'"
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
# 🔎 CÀO TRỰC TIẾP TỪ M.FACEBOOK.COM
# ============================================================

def read_page_feed(page_name, target_url):
    try:
        print(f"🔎 Đang cào trực tiếp: {page_name}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(target_url, headers=headers, timeout=15)
        if not response.ok:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        entries = []
        
        # Cào các bài viết dạng thẻ article trên bản mobile facebook
        for article in soup.find_all('article')[:5]:
            text_content = article.get_text(separator=" ", strip=True)
            if len(text_content) > 10:
                link_tag = article.find('a', href=True)
                # Lấy link chi tiết bài viết nếu có, không thì trỏ về page
                if link_tag and '/posts/' in link_tag['href']:
                    post_link = f"https://facebook.com{link_tag['href']}"
                else:
                    post_link = f"https://facebook.com/{page_name}"
                
                class DummyEntry:
                    pass
                entry = DummyEntry()
                entry.id = post_link
                entry.title = text_content[:200] + "..."
                entry.link = post_link
                entries.append(entry)

        print(f"   → {page_name}: tìm thấy {len(entries)} bài")
        return entries
    except Exception as error:
        print(f"❌ Lỗi cào trực tiếp {page_name}: {error}")
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
# 🧪 LỆNH TEST QUOTE VÀ TEST POST RIÊNG BIỆT
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
        
        entry = entries[0]
        title = getattr(entry, "title", "Bài viết mới")
        link = getattr(entry, "link", "")
        
        if not link:
            continue
            
        message = (
            f"🧪 **[TEST FACEBOOK POST]**\n\n"
            f"📄 **Page:** {page_name}\n\n"
            f"{title}\n\n"
            f"🔗 [Xem bài viết]({link})"
        )
        
        success = send_telegram(message)
        if success:
            return f"✅ Đã test gửi bài viết thành công từ page: <b>{page_name}</b>!"
            
    return "❌ Không tìm thấy bài viết nào để test."

# ============================================================
# 🚀 KHỞI ĐỘNG THREADS KHI IMPORT HOẶC CHẠY
# ============================================================

def start_background_tasks():
    if not BOT_TOKEN or BOT_TOKEN == "..":
        print("❌ CHƯA ĐIỀN BOT_TOKEN!")
        return

    fb_thread = threading.Thread(target=check_facebook, name="FacebookMonitor", daemon=True)
    fb_thread.start()

    q_thread = threading.Thread(target=check_quotes, name="QuoteScheduler", daemon=True)
    q_thread.start()

start_background_tasks()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
