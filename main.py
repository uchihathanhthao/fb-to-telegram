import time
import feedparser
import requests
import random
import threading
from datetime import datetime
import pytz
from flask import Flask

BOT_TOKEN = "8746522888:AAFZRNjOE8fa2O9XsBTyA3RnSBiNHOzHVaE"
CHAT_ID = "-1003910530474"

# ==============================================================================
# 1. CẤU HÌNH CÀO BÀI FACEBOOK (GIỮ NGUYÊN BẢN CỦA BẠN)
# ==============================================================================
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

RSS_FEEDS = [f"https://fetchrss.com/rss/feed?url=https://facebook.com/{page}" for page in PAGE_LIST]

sent_posts = set()
is_first_run = True

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
                for entry in feed.entries[:5]:
                    post_link = entry.link

                    if is_first_run:
                        sent_posts.add(post_link)
                    else:
                        if post_link not in sent_posts:
                            sent_posts.add(post_link)
                            send_telegram(entry.title, post_link)
            except Exception as e:
                print(f"Lỗi đọc feed {feed_url}: {e}")
        
        if is_first_run:
            is_first_run = False
            print("=> Đã lưu xong danh sách bài cũ! Từ bây giờ chỉ những bài đăng MỚI mới được gửi về Telegram.")

        time.sleep(900)

# ==============================================================================
# 2. CẤU HÌNH GỬI QUOTE TỰ ĐỘNG & THEO CHU KỲ SHUFFLE
# ==============================================================================
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

def get_next_quote():
    global quote_queue
    if not quote_queue:
        quote_queue = RAW_QUOTES.copy()
        random.shuffle(quote_queue)
    return quote_queue.pop(0)

def send_quote_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return str(e)

def check_quotes():
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    sent_slots = set()
    while True:
        now = datetime.now(tz)
        current_slot = None
        
        if now.hour == 5 and now.minute == 0: current_slot = "5AM"
        elif now.hour == 13 and now.minute == 0: current_slot = "1PM"
        elif now.hour == 22 and now.minute == 0: current_slot = "10PM"
            
        if current_slot and current_slot not in sent_slots:
            quote_text = get_next_quote()
            send_quote_msg(quote_text)
            sent_slots.add(current_slot)
            time.sleep(60)
            
        if now.minute != 0:
            sent_slots.clear()
            
        time.sleep(20)

# ==============================================================================
# 3. WEBSERVER FLASK VÀ ROUTE TEST
# ==============================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Telegram đang chạy 24/7 (Quét FB 15p/lần & Gửi Quote 5h, 13h, 22h)"

@app.route('/test')
def test_send():
    sample_quote = get_next_quote()
    res = send_quote_msg(f"🧪 **[TEST THỦ CÔNG]**\n\n{sample_quote}")
    return f"KẾT QUẢ GỬI TELEGRAM: {res}"

if __name__ == "__main__":
    # Khởi chạy Tiến trình 1: Cào Facebook
    t_fb = threading.Thread(target=check_feeds)
    t_fb.daemon = True
    t_fb.start()
    
    # Khởi chạy Tiến trình 2: Gửi Quote
    t_quote = threading.Thread(target=check_quotes)
    t_quote.daemon = True
    t_quote.start()
    
    # Khởi chạy Server Flask
    app.run(host='0.0.0.0', port=8080)
