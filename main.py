import os
import json
import time
import html
import random
import threading
from datetime import datetime, timedelta, timezone

import requests
from flask import Flask

# ============================================================
# 🔐 BÍ MẬT (đặt trong Render > Environment, KHÔNG viết vào code)
#   BOT_TOKEN   : token bot Telegram
#   APIFY_TOKEN : token tài khoản Apify
# ============================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")

# ============================================================
# ⚙️ TELEGRAM CHAT ID (nhóm/kênh nhận tin)
# ============================================================

CHAT_ID = os.environ.get("CHAT_ID", "-1003910530474")

# ============================================================
# 📘 CÁC PAGE FACEBOOK CẦN THEO DÕI
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
    "KyNangTDMU",
    "FFL.TDMU",
    "khoangoaingu.tdmu",
    # --- Các page thêm ngày 26/11 ---
    "hoisinhvien.com.vn",
    "doanhoitruongkinhtetaichinh",
    "DoanHoiVienDTKTXDVGT",
    "viencongngheso",
    "dtn.bhtcds",
    "hotronguoihocTDMU",
    "doanhoikhoacongnghiepvanhoa",
    "doanhoitlvqlpttdmu",
]

# Các page ít đăng bài (bài mới nhất là bài rất cũ). Quét thưa hơn, không dùng bộ lọc thời gian,
# vì bài ghim cũ có thể làm bộ lọc dừng quá sớm.
SLOW_PAGES = []  # hiện không có page nào ít đăng; thêm tên page vào đây nếu cần

FAST_PAGES = [p for p in PAGE_LIST if p not in SLOW_PAGES]

# ============================================================
# ⏱️ CẤU HÌNH QUÉT + CHI PHÍ APIFY
# ============================================================

APIFY_ACTOR = "alfalfa~facebook-posts-scraper"
APIFY_API = "https://api.apify.com/v2"

SCAN_INTERVAL_SEC = 30 * 60        # quét nhóm page chính mỗi 30 phút
WINDOW_MIN = 75                    # mỗi lần chỉ xin bài đăng trong 75 phút gần nhất
RESULTS_LIMIT_FAST = 10            # tối đa 10 bài / page / lần quét
MAX_AGE_HOURS_FAST = 6             # chốt an toàn: bỏ qua bài cũ hơn 6 giờ
MAX_CHARGE_FAST_USD = 0.10         # trần chi phí cho 1 lần quét (khoảng 50 bài)

SLOW_INTERVAL_SEC = 12 * 3600      # nhóm page ít đăng: quét mỗi 12 giờ
RESULTS_LIMIT_SLOW = 3
MAX_AGE_HOURS_SLOW = 72
MAX_CHARGE_SLOW_USD = 0.05

MAX_SEND_PER_SCAN = 20             # chống gửi quá nhiều tin một lúc
PREVIEW_CHARS = 350                # số ký tự xem trước của bài

VN_TZ = timezone(timedelta(hours=7))  # giờ Việt Nam (UTC+7, không đổi giờ mùa hè)


def page_url(page):
    """Tạo link Facebook từ tên page hoặc ID số."""
    if page.isdigit():
        return f"https://www.facebook.com/profile.php?id={page}"
    return f"https://www.facebook.com/{page}"


# ============================================================
# 🧠 BỘ NHỚ (bài đã gửi, trạng thái quét)
# ============================================================

sent_posts = {}                    # khóa của bài (link, giờ đăng) -> thời điểm đã gửi
posts_lock = threading.Lock()
state_dirty = False                # True khi có bài mới được ghi nhớ mà chưa lưu lên Apify
state_store_id = None              # ID kho lưu trạng thái trên Apify (None = chưa dùng được)
STATE_STORE_NAME = "fb-bot-state"  # tên kho lưu (key-value store) trên tài khoản Apify của bạn
STATE_RECORD_KEY = "sent_posts"

status = {
    "started_at": datetime.now(VN_TZ).strftime("%d/%m/%Y %H:%M:%S"),
    "last_scan": "chưa quét lần nào",
    "last_result": "-",
    "scans_ok": 0,
    "scans_failed": 0,
    "posts_sent": 0,
    "persist": "chưa kiểm tra",
}

# ============================================================
# 💬 QUOTES
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
    "Cuộc đua này không có người giỏi nhất, chỉ có người kiên trì nhất.",
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

def send_telegram(text, html_mode=False):
    """Gửi tin nhắn. Tự thử lại tối đa 3 lần khi mạng chậm."""
    if not BOT_TOKEN:
        print("❌ Chưa có BOT_TOKEN trong Environment của Render.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    if html_mode:
        payload["parse_mode"] = "HTML"

    for attempt in range(1, 4):
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.ok:
                return True
            print(f"Telegram HTTP {response.status_code}: {response.text[:300]}")
            if response.status_code == 429:
                try:
                    wait = int(response.json().get("parameters", {}).get("retry_after", 5))
                except Exception:
                    wait = 5
                time.sleep(min(wait, 30))
                continue
            if response.status_code in (400, 401, 403, 404):
                return False  # lỗi cố định (token/nhóm/nội dung), thử lại vô ích
        except requests.RequestException as error:
            # Chỉ in tên lỗi, KHÔNG in nội dung lỗi vì có thể chứa token trong đường link.
            print(f"⚠️ Lỗi kết nối Telegram (lần {attempt}/3): {type(error).__name__}")
        time.sleep(3 * attempt)
    return False


# ============================================================
# 🔎 LẤY BÀI TỪ FACEBOOK QUA APIFY
# ============================================================

def _apify_headers():
    return {"Authorization": f"Bearer {APIFY_TOKEN}"}


def run_apify(urls, results_limit, newer_than=None, max_charge=0.10):
    """Chạy actor lấy bài Facebook, chờ xong và trả về danh sách bài."""
    input_data = {
        "startUrls": [{"url": u} for u in urls],
        "resultsLimit": results_limit,
    }
    if newer_than:
        input_data["onlyPostsNewerThan"] = newer_than

    response = requests.post(
        f"{APIFY_API}/acts/{APIFY_ACTOR}/runs",
        params={"maxTotalChargeUsd": max_charge, "timeout": 600},
        json=input_data,
        headers=_apify_headers(),
        timeout=30,
    )
    response.raise_for_status()
    run = response.json()["data"]
    run_id = run["id"]
    dataset_id = run["defaultDatasetId"]
    run_status = run.get("status", "READY")

    deadline = time.time() + 15 * 60
    while run_status in ("READY", "RUNNING", "TIMING-OUT", "ABORTING"):
        if time.time() > deadline:
            raise RuntimeError("Apify chạy quá lâu (hơn 15 phút)")
        poll = requests.get(
            f"{APIFY_API}/actor-runs/{run_id}",
            params={"waitForFinish": 30},
            headers=_apify_headers(),
            timeout=60,
        )
        poll.raise_for_status()
        run_status = poll.json()["data"]["status"]

    if run_status != "SUCCEEDED":
        raise RuntimeError(f"Apify kết thúc với trạng thái {run_status}")

    items = requests.get(
        f"{APIFY_API}/datasets/{dataset_id}/items",
        params={"format": "json"},
        headers=_apify_headers(),
        timeout=60,
    )
    items.raise_for_status()
    data = items.json()
    return data if isinstance(data, list) else []


# ============================================================
# 💾 NHỚ BÀI ĐÃ GỬI (chống gửi trùng, kể cả khi bot khởi động lại)
#    Danh sách được lưu trên Apify (kho "fb-bot-state"), vì ổ đĩa của Render
#    gói Free bị xóa mỗi lần khởi động lại.
# ============================================================

def normalize_url(url):
    """Bỏ phần đuôi ?... của link bài (phần này có thể thay đổi giữa các lần lấy)."""
    base, _, _ = url.partition("?")
    if base.endswith(".php"):   # kiểu permalink.php?story_fbid=... thì phần sau ? là phần quan trọng
        return url
    return base.rstrip("/")


def post_keys(item):
    """Các 'dấu vân tay' của một bài: link (đã chuẩn hóa) và cặp (page, giờ đăng).
    Chỉ cần trùng một trong hai là coi như bài đã gửi."""
    keys = []
    link = item.get("url") or item.get("topLevelUrl")
    if link:
        keys.append("u:" + normalize_url(link))
    post_time = parse_post_time(item)
    page = item.get("pageName") or item.get("facebookUrl")
    if post_time and page:
        keys.append(f"t:{page}:{int(post_time.timestamp())}")
    return keys


def load_state():
    """Nạp danh sách bài đã gửi từ Apify. Trả về True nếu thành công."""
    global state_store_id
    try:
        response = requests.post(
            f"{APIFY_API}/key-value-stores",
            params={"name": STATE_STORE_NAME},   # đã có thì trả về kho cũ, chưa có thì tạo mới
            headers=_apify_headers(),
            timeout=30,
        )
        response.raise_for_status()
        store_id = response.json()["data"]["id"]

        record = requests.get(
            f"{APIFY_API}/key-value-stores/{store_id}/records/{STATE_RECORD_KEY}",
            headers=_apify_headers(),
            timeout=30,
        )
        data = {}
        if record.status_code != 404:
            record.raise_for_status()
            data = record.json()

        cutoff = time.time() - 3 * 86400
        loaded = 0
        if isinstance(data, dict):
            with posts_lock:
                for key, stamp in data.items():
                    if isinstance(stamp, (int, float)) and stamp >= cutoff and key not in sent_posts:
                        sent_posts[key] = stamp
                        loaded += 1
        state_store_id = store_id
        status["persist"] = "BẬT"
        print(f"💾 Bộ nhớ bền sẵn sàng, đã nạp {loaded} bài đã gửi.")
        return True
    except Exception as error:
        state_store_id = None
        status["persist"] = "TẮT (không kết nối được kho lưu trên Apify)"
        print(f"⚠️ Chưa dùng được bộ nhớ bền: {type(error).__name__}: {str(error)[:150]}")
        return False


def save_state():
    """Lưu danh sách bài đã gửi lên Apify. Trả về True nếu thành công."""
    global state_dirty
    if not state_store_id:
        return False
    try:
        with posts_lock:
            snapshot = dict(sent_posts)
        response = requests.put(
            f"{APIFY_API}/key-value-stores/{state_store_id}/records/{STATE_RECORD_KEY}",
            data=json.dumps(snapshot).encode("utf-8"),
            headers={**_apify_headers(), "Content-Type": "application/json; charset=utf-8"},
            timeout=30,
        )
        response.raise_for_status()
        state_dirty = False
        return True
    except Exception as error:
        print(f"⚠️ Lưu bộ nhớ bền thất bại: {type(error).__name__}: {str(error)[:150]}")
        return False


# ============================================================
# ✉️ ĐỊNH DẠNG TIN NHẮN BÀI ĐĂNG
# ============================================================

def parse_post_time(item):
    """Đọc thời gian đăng bài, trả về datetime (UTC) hoặc None."""
    raw = item.get("time")
    if isinstance(raw, str) and raw:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    stamp = item.get("timestamp")
    if isinstance(stamp, (int, float)) and stamp > 0:
        if stamp > 1e12:  # mili giây
            stamp = stamp / 1000
        return datetime.fromtimestamp(stamp, tz=timezone.utc)
    return None


def make_preview(text, limit=PREVIEW_CHARS):
    text = (text or "").strip()
    if not text:
        return "(Bài đăng chỉ có hình ảnh hoặc video, không có chữ)"
    lines = [line.strip() for line in text.splitlines()]
    cleaned = []
    for line in lines:
        if line or (cleaned and cleaned[-1]):
            cleaned.append(line)
    text = "\n".join(cleaned).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut[limit // 2:]:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip() + "…"


def format_post_message(item, test=False):
    page = item.get("pageName") or "Facebook"
    link = item.get("url") or item.get("topLevelUrl") or ""
    post_time = parse_post_time(item)
    when = post_time.astimezone(VN_TZ).strftime("%H:%M %d/%m/%Y") if post_time else "không rõ"

    header = "🧪 <b>[TEST]</b> " if test else ""
    return (
        f"{header}📢 <b>{html.escape(str(page))}</b>\n"
        f"🕒 {when} (giờ VN)\n\n"
        f"{html.escape(make_preview(item.get('text')))}\n\n"
        f"🔗 <a href=\"{html.escape(link, quote=True)}\">Xem bài viết</a>"
    )


def process_items(items, max_age_hours, seed_only=False):
    """Gửi các bài chưa gửi sang Telegram. Trả về số bài đã gửi."""
    now = datetime.now(timezone.utc)
    fresh = []
    for item in items:
        link = item.get("url") or item.get("topLevelUrl")
        if not link:
            continue
        post_time = parse_post_time(item)
        if post_time and now - post_time > timedelta(hours=max_age_hours):
            continue  # bài quá cũ: bỏ qua
        fresh.append((post_time or now, link, item))

    fresh.sort(key=lambda row: row[0])  # cũ trước, mới sau

    # Lọc ra các bài chưa từng gửi và ghi nhớ ngay (để không bị gửi trùng)
    global state_dirty
    pending = []
    with posts_lock:
        for _, link, item in fresh:
            keys = post_keys(item)
            if any(k in sent_posts for k in keys):
                continue  # đã gửi rồi
            stamp = time.time()
            for k in keys:
                sent_posts[k] = stamp
            pending.append((keys, link, item))
            state_dirty = True

    if seed_only:
        return 0

    if len(pending) > MAX_SEND_PER_SCAN:
        print(f"⚠️ Có {len(pending)} bài mới, chỉ gửi {MAX_SEND_PER_SCAN} bài mới nhất.")
        pending = pending[-MAX_SEND_PER_SCAN:]

    sent = 0
    for keys, link, item in pending:
        if send_telegram(format_post_message(item), html_mode=True):
            sent += 1
            print(f"✅ ĐÃ GỬI | {item.get('pageName')} | {link}")
        else:
            with posts_lock:
                for k in keys:
                    sent_posts.pop(k, None)  # gửi lỗi: cho phép thử lại ở lần quét sau
            print(f"❌ GỬI THẤT BẠI | {item.get('pageName')} | {link}")

    # dọn bộ nhớ: bỏ bài đã nhớ quá 3 ngày
    cutoff = time.time() - 3 * 86400
    with posts_lock:
        for key in [k for k, v in sent_posts.items() if v < cutoff]:
            del sent_posts[key]
    return sent


# ============================================================
# 🔄 VÒNG LẶP QUÉT FACEBOOK
# ============================================================

def check_facebook():
    print("=" * 60)
    print("🚀 BOT QUÉT FACEBOOK (APIFY) KHỞI ĐỘNG")
    print(f"📌 Page quét thường xuyên: {len(FAST_PAGES)} | page ít đăng: {len(SLOW_PAGES)}")
    print(f"⏱️ Chu kỳ: {SCAN_INTERVAL_SEC // 60} phút | cửa sổ bài mới: {WINDOW_MIN} phút")
    print("=" * 60)

    fail_count = 0
    last_slow = 0.0
    slow_seeded = False

    while True:
        started = time.time()

        # Nạp danh sách bài đã gửi từ Apify (thử lại mỗi vòng nếu lần trước thất bại)
        if not state_store_id:
            load_state()

        # --- Nhóm page chính ---
        try:
            newer = (datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MIN)).strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            )
            items = run_apify(
                [page_url(p) for p in FAST_PAGES],
                RESULTS_LIMIT_FAST,
                newer_than=newer,
                max_charge=MAX_CHARGE_FAST_USD,
            )
            sent = process_items(items, MAX_AGE_HOURS_FAST)
            print(f"🔎 Quét xong: Apify trả {len(items)} bài, đã gửi {sent} bài mới.")
            status["last_result"] = f"OK: Apify trả {len(items)} bài, gửi {sent} bài mới"
            status["scans_ok"] += 1
            status["posts_sent"] += sent
            if fail_count >= 3:
                send_telegram("✅ Bot đã quét lại Facebook bình thường.")
            fail_count = 0
        except Exception as error:
            fail_count += 1
            status["last_result"] = f"LỖI: {type(error).__name__}: {str(error)[:150]}"
            status["scans_failed"] += 1
            print(f"⚠️ Quét thất bại ({fail_count} lần liên tiếp): {type(error).__name__}: {str(error)[:200]}")
            if fail_count == 3:
                send_telegram(
                    "⚠️ Bot không lấy được bài Facebook 3 lần liên tiếp. "
                    "Hãy kiểm tra credit/token trên Apify và log trên Render."
                )
        status["last_scan"] = datetime.now(VN_TZ).strftime("%d/%m/%Y %H:%M:%S")
        if state_dirty:
            save_state()

        # --- Nhóm page ít đăng ---
        if SLOW_PAGES and time.time() - last_slow >= SLOW_INTERVAL_SEC:
            try:
                items = run_apify(
                    [page_url(p) for p in SLOW_PAGES],
                    RESULTS_LIMIT_SLOW,
                    newer_than=None,
                    max_charge=MAX_CHARGE_SLOW_USD,
                )
                # Lần đầu chỉ ghi nhớ bài hiện có, không gửi (tránh gửi lại bài cũ).
                sent = process_items(items, MAX_AGE_HOURS_SLOW, seed_only=not slow_seeded)
                slow_seeded = True
                last_slow = time.time()
                print(f"🔎 Quét page ít đăng xong: gửi {sent} bài mới.")
            except Exception as error:
                print(f"⚠️ Quét page ít đăng thất bại: {type(error).__name__}: {str(error)[:200]}")
            if state_dirty:
                save_state()

        elapsed = time.time() - started
        time.sleep(max(60, SCAN_INTERVAL_SEC - elapsed))


# ============================================================
# ⏰ QUOTE + NHẮC GIỜ "PHẢI HƠN ĐIỂM THẰNG BẢO!"
# ============================================================

QUOTE_HOURS = {5, 13, 22}                       # gửi quote lúc 05:00, 13:00, 22:00
BAO_HOURS = {0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22}  # nhắc mỗi 2 tiếng


def check_quotes():
    print("💬 Hệ thống Quote và Nhắc nhở đã khởi chạy.")
    done = set()

    while True:
        try:
            now = datetime.now(VN_TZ)
            day = now.strftime("%Y-%m-%d")

            # Trong 5 phút đầu của giờ đó, nếu chưa gửi thì gửi (có cơ hội thử lại nếu lỗi mạng)
            if now.minute < 5:
                quote_key = f"{day} quote {now.hour}"
                if now.hour in QUOTE_HOURS and quote_key not in done:
                    print(f"💬 Đang gửi quote {now.hour:02d}:00...")
                    if send_telegram(get_next_quote()):
                        done.add(quote_key)

                bao_key = f"{day} bao {now.hour}"
                if now.hour in BAO_HOURS and bao_key not in done:
                    print(f"🔥 Đang gửi nhắc nhở {now.hour:02d}:00...")
                    if send_telegram("PHẢI HƠN ĐIỂM THẰNG BẢO!"):
                        done.add(bao_key)

            # dọn các mốc của ngày cũ
            for key in [k for k in done if not k.startswith(day)]:
                done.discard(key)

            time.sleep(20)
        except Exception as error:
            print(f"❌ Lỗi hệ thống quote: {type(error).__name__}")
            time.sleep(30)


# ============================================================
# 🌐 FLASK WEB SERVER (để UptimeRobot ping giữ bot thức)
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "✅ Bot đang chạy 24/7."


@app.route("/health")
def health():
    return "OK", 200


@app.route("/status")
def show_status():
    lines = [
        f"Khởi động lúc: {status['started_at']}",
        f"Lần quét gần nhất: {status['last_scan']}",
        f"Kết quả: {status['last_result']}",
        f"Số lần quét OK / lỗi: {status['scans_ok']} / {status['scans_failed']}",
        f"Số bài đã gửi từ lúc khởi động: {status['posts_sent']}",
        f"Bộ nhớ chống gửi trùng khi khởi động lại: {status['persist']} (đang nhớ {len(sent_posts)} khóa)",
        f"Có BOT_TOKEN: {'có' if BOT_TOKEN else 'KHÔNG'} | Có APIFY_TOKEN: {'có' if APIFY_TOKEN else 'KHÔNG'}",
    ]
    return "<br>".join(html.escape(line) for line in lines)


@app.route("/test")
def test_send():
    ok = send_telegram("🧪 TEST BOT: kết nối Telegram thành công!")
    return "✅ TEST THÀNH CÔNG!" if ok else "❌ TEST THẤT BẠI! (xem Logs trên Render)"


@app.route("/testquote")
def test_quote():
    ok = send_telegram(f"🧪 [TEST QUOTE]\n\n{get_next_quote()}")
    return "✅ Đã gửi quote thử." if ok else "❌ Gửi quote thất bại!"


@app.route("/testbao")
def test_bao():
    ok = send_telegram("PHẢI HƠN ĐIỂM THẰNG BẢO!")
    return "✅ Đã gửi câu nhắc." if ok else "❌ Thất bại!"


def _run_test_post():
    try:
        items = run_apify([page_url("tuoitredhthudaumot")], 1, None, 0.05)
        if not items:
            print("🧪 testpost: Apify không trả về bài nào.")
            return
        ok = send_telegram(format_post_message(items[0], test=True), html_mode=True)
        print(f"🧪 testpost: gửi {'OK' if ok else 'THẤT BẠI'}")
    except Exception as error:
        print(f"🧪 testpost lỗi: {type(error).__name__}: {str(error)[:200]}")


@app.route("/testpost")
def test_post():
    if not APIFY_TOKEN:
        return "❌ Chưa có APIFY_TOKEN trong Environment của Render."
    threading.Thread(target=_run_test_post, daemon=True).start()
    return "⏳ Đang lấy thử 1 bài của page tuoitredhthudaumot. Chờ 1-2 phút rồi xem Telegram."


# ============================================================
# 🚀 KHỞI ĐỘNG CÁC LUỒNG NỀN
# ============================================================

_started = False


def start_background_tasks():
    global _started
    if _started:
        return
    _started = True

    if not BOT_TOKEN:
        print("❌ CHƯA CÓ BOT_TOKEN! Hãy thêm biến BOT_TOKEN trong Render > Environment.")
        return

    threading.Thread(target=check_quotes, name="QuoteScheduler", daemon=True).start()

    if APIFY_TOKEN:
        threading.Thread(target=check_facebook, name="FacebookMonitor", daemon=True).start()
    else:
        print("❌ CHƯA CÓ APIFY_TOKEN! Bot chỉ gửi quote, chưa quét Facebook.")


start_background_tasks()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), threaded=True)
