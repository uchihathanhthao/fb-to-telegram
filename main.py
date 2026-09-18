```python
import time
import feedparser
import requests
import random
import threading
from datetime import datetime
import pytz
from flask import Flask

# ============================================================
# 🔐 TELEGRAM BOT TOKEN
# 👉 CHỈ CẦN ĐIỀN TOKEN MỚI VÀO DÒNG NÀY
# ============================================================

BOT_TOKEN = "8746522888:AAE1drDmhydNlZB5YAkO82_u8ZzNsmZ_LxY"

# ============================================================
# ⚙️ TELEGRAM
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

RSS_FEEDS = {
    page: f"https://fetchrss.com/rss/feed?url=https://facebook.com/{page}"
    for page in PAGE_LIST
}

# ============================================================
# 🧠 BỘ NHỚ BÀI ĐÃ GỬI
# ============================================================

sent_posts = set()

# Dùng Lock để tránh 2 thread cùng thao tác dữ liệu
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
    """
    Gửi tin nhắn Telegram.
    Có kiểm tra status code + response thật.
    """

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=15
        )

        print(
            f"Telegram HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

        if response.ok:
            return True

        return False

    except requests.RequestException as error:
        print(f"❌ Lỗi kết nối Telegram: {error}")
        return False

    except Exception as error:
        print(f"❌ Lỗi Telegram không xác định: {error}")
        return False


# ============================================================
# 📢 GỬI THÔNG BÁO BÀI FACEBOOK
# ============================================================

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
        print(
            f"✅ ĐÃ GỬI | {page_name} | {title}"
        )
    else:
        print(
            f"❌ GỬI THẤT BẠI | {page_name} | {title}"
        )

    return success


# ============================================================
# 🔎 ĐỌC RSS CỦA MỘT PAGE
# ============================================================

def read_page_feed(page_name, feed_url):

    try:

        print(f"🔎 Đang kiểm tra: {page_name}")

        feed = feedparser.parse(feed_url)

        # feedparser có thể không ném exception,
        # nên phải kiểm tra bozo / entries.
        if getattr(feed, "bozo", False):
            print(
                f"⚠️ RSS có lỗi: {page_name} | "
                f"{getattr(feed, 'bozo_exception', 'Unknown error')}"
            )

        entries = feed.entries[:10]

        print(
            f"   → {page_name}: "
            f"tìm thấy {len(entries)} bài"
        )

        return entries

    except Exception as error:

        print(
            f"❌ Lỗi đọc RSS {page_name}: {error}"
        )

        return []


# ============================================================
# 🧹 LẤY ID DUY NHẤT CHO MỖI BÀI
# ============================================================

def get_post_id(entry):

    # Ưu tiên id của RSS
    if getattr(entry, "id", None):
        return str(entry.id)

    # Nếu không có thì dùng link
    if getattr(entry, "link", None):
        return str(entry.link)

    return None


# ============================================================
# 🆕 QUÉT FACEBOOK
# ============================================================

def check_facebook():

    first_run = True

    print("=" * 60)
    print("🚀 FACEBOOK → TELEGRAM BOT KHỞI ĐỘNG")
    print(f"📌 Số Page: {len(PAGE_LIST)}")
    print("⏱️ Chu kỳ quét: 5 phút")
    print("=" * 60)

    while True:

        cycle_start = time.time()

        if first_run:
            print(
                "\n🟡 LẦN CHẠY ĐẦU TIÊN:"
            )
            print(
                "Bot sẽ ghi nhận các bài đang tồn tại "
                "nhưng KHÔNG gửi chúng."
            )
        else:
            print(
                "\n🔵 ĐANG QUÉT BÀI VIẾT MỚI..."
            )

        for page_name, feed_url in RSS_FEEDS.items():

            entries = read_page_feed(
                page_name,
                feed_url
            )

            # Không có dữ liệu
            if not entries:
                continue

            # RSS thường sắp xếp bài mới trước.
            # Xử lý tối đa 10 bài gần nhất.
            for entry in reversed(entries):

                post_id = get_post_id(entry)

                if not post_id:
                    print(
                        f"⚠️ Không lấy được ID bài: "
                        f"{page_name}"
                    )
                    continue

                title = getattr(
                    entry,
                    "title",
                    "Bài viết mới"
                )

                link = getattr(
                    entry,
                    "link",
                    ""
                )

                if not link:
                    continue

                # --------------------------------------------
                # LẦN ĐẦU: CHỈ LƯU BÀI CŨ
                # --------------------------------------------

                if first_run:

                    with posts_lock:
                        sent_posts.add(post_id)

                    continue

                # --------------------------------------------
                # CÁC LẦN SAU: PHÁT HIỆN BÀI MỚI
                # --------------------------------------------

                with posts_lock:

                    if post_id in sent_posts:
                        continue

                    # Đánh dấu TRƯỚC khi gửi để tránh
                    # nhiều vòng xử lý cùng gửi trùng.
                    sent_posts.add(post_id)

                print(
                    f"\n🆕 PHÁT HIỆN BÀI MỚI!"
                )
                print(
                    f"   Page: {page_name}"
                )
                print(
                    f"   Title: {title}"
                )
                print(
                    f"   Link: {link}"
                )

                success = send_facebook_post(
                    page_name,
                    title,
                    link
                )

                # Nếu Telegram thất bại,
                # cho phép lần quét sau gửi lại.
                if not success:

                    with posts_lock:
                        sent_posts.discard(post_id)

        # --------------------------------------------
        # KẾT THÚC FIRST RUN
        # --------------------------------------------

        if first_run:

            first_run = False

            print(
                "\n✅ ĐÃ HOÀN TẤT KHỞI TẠO."
            )

            print(
                f"📦 Đã ghi nhận "
                f"{len(sent_posts)} bài cũ."
            )

            print(
                "📢 Từ bây giờ chỉ bài MỚI "
                "mới được gửi Telegram."
            )

        elapsed = time.time() - cycle_start

        print(
            f"\n⏱️ Chu kỳ hoàn tất sau "
            f"{elapsed:.1f} giây."
        )

        print(
            "💤 Nghỉ 5 phút trước lần quét tiếp theo..."
        )

        time.sleep(300)


# ============================================================
# ⏰ HỆ THỐNG QUOTE
# ============================================================

def check_quotes():

    timezone = pytz.timezone(
        "Asia/Ho_Chi_Minh"
    )

    # Lưu các slot đã gửi trong ngày.
    sent_slots = set()

    print(
        "💬 Hệ thống Quote đã khởi chạy."
    )

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

            # --------------------------------------------
            # GỬI QUOTE
            # --------------------------------------------

            if slot and slot not in sent_slots:

                quote = get_next_quote()

                print(
                    f"💬 Đang gửi quote {slot}..."
                )

                success = send_telegram(
                    quote
                )

                if success:

                    sent_slots.add(slot)

                    print(
                        f"✅ Quote {slot} đã gửi."
                    )

                else:

                    print(
                        f"❌ Quote {slot} gửi thất bại."
                    )

                # Tránh gửi lại nhiều lần
                # trong cùng phút.
                time.sleep(60)

            # --------------------------------------------
            # SANG NGÀY MỚI
            # --------------------------------------------

            if now.hour == 0 and now.minute == 1:

                sent_slots.clear()

                print(
                    "🔄 Đã reset lịch quote cho ngày mới."
                )

                time.sleep(60)

            time.sleep(20)

        except Exception as error:

            print(
                f"❌ Lỗi hệ thống quote: {error}"
            )

            time.sleep(30)


# ============================================================
# 🌐 FLASK WEB SERVER
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():

    return (
        "✅ Facebook → Telegram Bot đang chạy 24/7.<br>"
        "📡 Facebook: quét mỗi 5 phút.<br>"
        "💬 Quote: 05:00 / 13:00 / 22:00."
    )


# ============================================================
# 🧪 TEST TELEGRAM
# ============================================================

@app.route("/test")
def test_send():

    test_message = (
        "🧪 **TEST TELEGRAM BOT**\n\n"
        "Nếu bạn nhận được tin nhắn này "
        "thì kết nối Telegram đang hoạt động."
    )

    success = send_telegram(
        test_message
    )

    if success:

        return (
            "✅ TEST THÀNH CÔNG! "
            "Hãy kiểm tra Telegram."
        )

    return (
        "❌ TEST THẤT BẠI! "
        "Hãy xem Logs trên Render."
    )


# ============================================================
# ❤️ HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return "OK", 200


# ============================================================
# 🚀 KHỞI ĐỘNG
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("🤖 FACEBOOK → TELEGRAM AUTOMATION BOT")
    print("=" * 60)

    # --------------------------------------------
    # Kiểm tra cấu hình cơ bản
    # --------------------------------------------

    if (
        not BOT_TOKEN
        or BOT_TOKEN == "DÁN_TOKEN_TELEGRAM_MỚI_CỦA_BẠN_VÀO_ĐÂY"
    ):

        print(
            "❌ CHƯA ĐIỀN BOT_TOKEN!"
        )

        raise SystemExit(
            "Hãy điền Telegram Bot Token vào dòng BOT_TOKEN."
        )

    if not CHAT_ID:

        raise SystemExit(
            "❌ CHAT_ID đang trống."
        )

    # --------------------------------------------
    # THREAD FACEBOOK
    # --------------------------------------------

    facebook_thread = threading.Thread(
        target=check_facebook,
        name="FacebookMonitor",
        daemon=True
    )

    facebook_thread.start()

    # --------------------------------------------
    # THREAD QUOTE
    # --------------------------------------------

    quote_thread = threading.Thread(
        target=check_quotes,
        name="QuoteScheduler",
        daemon=True
    )

    quote_thread.start()

    # --------------------------------------------
    # FLASK
    # --------------------------------------------

    port = 8080

    print(
        f"🌐 Web server chạy tại port {port}"
    )

    app.run(
        host="0.0.0.0",
        port=port,
        threaded=True
    )
```
