# Facebook Messenger Q&A Bot (CSV-based)

Một bot trả lời tự động trên Facebook Messenger dựa vào file CSV gồm 2 cột **Hỏi** và **Trả lời**.

## 1) Chuẩn bị file CSV 
- Tạo `qna.csv` với 2 cột: `Hỏi` và `Trả lời` (có thể dùng `Hoi/Question` và `Tra_loi/Answer`).
- Mỗi dòng là một cặp Hỏi–Đáp.
- Mã nguồn hỗ trợ chữ có dấu/không dấu và so khớp mơ hồ (fuzzy).

## 2) Tạo Facebook App/Page và token
1. Tạo Fanpage (nếu chưa có).
2. Vào developers.facebook.com tạo App, thêm sản phẩm **Messenger**.
3. Tạo **Page Access Token** và gán vào biến môi trường `PAGE_ACCESS_TOKEN`.
4. Đặt **VERIFY_TOKEN** (chuỗi bí mật tự chọn) để xác minh Webhook.

## 3) Chạy bot cục bộ
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # điền token thật
python app.py
```
Mặc định chạy ở `http://localhost:8000`.

## 4) Expose webhook (ngrok)
```bash
ngrok http 8000
```
Nhận URL dạng `https://xxx.ngrok.io`. Vào phần **Webhook** trong app Messenger:
- Callback URL: `https://xxx.ngrok.io/webhook`
- Verify Token: trùng với `VERIFY_TOKEN`.
- Subscriptions: chọn `messages`, `messaging_postbacks`.

## 5) Triển khai
- Có thể deploy lên Render/Heroku/Fly.io/VPS. Chỉ cần set biến môi trường và trỏ webhook về `/webhook`.

## 6) Tùy chỉnh khớp câu hỏi
- Ngưỡng so khớp `MATCH_THRESHOLD` (0–100). Mặc định 80–85 là hợp lý.
- Chuẩn hoá văn bản: hạ chữ thường, bỏ dấu tiếng Việt, xoá dấu câu.
- Thuật toán: `token_set_ratio` của RapidFuzz.

## 7) Gợi ý nâng cao
- Thêm từ khoá ưu tiên (ví dụ: "giá", "khuyến mãi") để tăng điểm.
- Log hội thoại để cải thiện CSV.
- Nút “Gặp nhân viên” khi không khớp.
- Thêm cache khi CSV lớn.

## 8) Kiểm tra nhanh
- `GET /health` trả `{status: ok, q_count: N}`.
- Gửi tin nhắn vào page để thử.