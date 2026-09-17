import time
import feedparser
import requests
import threading
from flask import Flask

BOT_TOKEN = "8746522888:AAFZRNjOE8fa2O9XsBTyA3RnSBiNHOzHVaE"
CHAT_ID = "-1003910530474"

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

# Tự động tạo link RSS cho từng Fanpage
RSS_FEEDS = [f"https://fetchrss.com/rss/feed?url=https://facebook.com/{page}" for page in PAGE_LIST]

# Tập hợp lưu trữ các link đã gửi (Chống gửi lặp lại 100%)
sent_posts = set()
is_first_run = True  # Cờ đánh dấu lần đầu chạy để bỏ qua bài cũ

def send_telegram(title, link):
    message = f"📢 **Bài viết mới!**\n\n{title}\n\n🔗 [Xem bài viết]({link})"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": message, 
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, json=payload, timeout=10)
        print(f"-> Đã gửi Telegram thành công: {title}")
    except Exception as e:
        print("Lỗi gửi Telegram:", e)

def check_feeds():
    global is_first_run
    while True:
        if is_first_run:
            print("Đang khởi tạo: Lấy danh sách bài hiện có làm bài cũ (Không gửi Telegram)...")
        else:
            print("Đang quét bài MỚI từ các Page (Chu kỳ 15 phút)...")

        for feed_url in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                # Đọc các bài viết gần đây nhất của từng Page
                for entry in feed.entries[:5]:
                    post_link = entry.link

                    if is_first_run:
                        # Lần chạy đầu: Đánh dấu tất cả bài hiện tại là ĐÃ ĐỌC để không bắn bài cũ
                        sent_posts.add(post_link)
                    else:
                        # Các lần chạy sau: Chỉ gửi nếu bài viết CHƯA TỪNG CÓ trong bộ nhớ sent_posts
                        if post_link not in sent_posts:
                            sent_posts.add(post_link)  # Lưu lại ngay để không bao giờ gửi lại
                            send_telegram(entry.title, post_link)
            except Exception as e:
                print(f"Lỗi đọc feed {feed_url}: {e}")
        
        # Sau khi chạy qua vòng đầu tiên, tắt cờ is_first_run
        if is_first_run:
            is_first_run = False
            print("=> Đã lưu xong danh sách bài cũ! Từ bây giờ chỉ những bài đăng MỚI mới được gửi về Telegram.")

        # Nghỉ 15 phút (900 giây) trước khi quét lần tiếp theo
        time.sleep(900)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot đang chạy 24/7 - Tự động quét bài mới mỗi 15 phút!"

if __name__ == "__main__":
    t = threading.Thread(target=check_feeds)
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=8080)
