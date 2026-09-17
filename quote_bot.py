import time
import requests
import random
from datetime import datetime
import pytz

BOT_TOKEN = "8746522888:AAFZRNjOE8fa2O9XsBTyA3RnSBiNHOzHVaE"
CHAT_ID = "-1003910530474"

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
    # Nếu hàng đợi rỗng, xáo trộn lại danh sách quote để lặp lại chu kỳ mới
    if not quote_queue:
        quote_queue = RAW_QUOTES.copy()
        random.shuffle(quote_queue)
        print("=> Đã lặp lại chu kỳ mới: Xáo trộn danh sách quote!")
    return quote_queue.pop(0)

def send_quote():
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    sent_slots = set()
    
    print("Bot Quote (5h sáng, 13h trưa, 22h đêm) đã sẵn sàng...")
    
    while True:
        now = datetime.now(tz)
        current_time_slot = None
        
        # Kiểm tra các khung giờ: 05:00, 13:00, 22:00
        if now.hour == 5 and now.minute == 0:
            current_time_slot = "5AM"
        elif now.hour == 13 and now.minute == 0:
            current_time_slot = "1PM"
        elif now.hour == 22 and now.minute == 0:
            current_time_slot = "10PM"
            
        # Gửi tin nhắn nếu rơi vào đúng khung giờ và chưa gửi trong phút đó
        if current_time_slot and current_time_slot not in sent_slots:
            quote_text = get_next_quote()
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": CHAT_ID,
                "text": quote_text,
                "parse_mode": "Markdown"
            }
            try:
                requests.post(url, json=payload, timeout=10)
                print(f"[{now}] Đã gửi quote khung giờ {current_time_slot} thành công!")
            except Exception as e:
                print("Lỗi gửi Telegram:", e)
                
            sent_slots.add(current_time_slot)
            time.sleep(60) # Chờ qua phút 00 để không gửi lặp lại
            
        # Reset lại cờ khi qua phút khác
        if now.minute != 0:
            sent_slots.clear()
            
        time.sleep(20) # Kiểm tra đồng hồ 20s/lần

if __name__ == "__main__":
    send_quote()
