import os
import csv
import string
import requests
from flask import Flask, request, jsonify
from rapidfuzz import process, fuzz
from unidecode import unidecode

PAGE_ACCESS_TOKEN = 'EAAL4B1zM9EYBPhqSg0h6kCKwALPZCZCSxYGACheXP4hzrXSricaAHvpIyYZBNbKXfBERmCOXkSmQ2dAeeh194ZABwrrC9zhLm90c3uIbKXKwAjGMvTytBdRr9DIzHgZCharfPwcF4mJqYOjKnwQbZCY1WQnT97U4GOavx4DyHNU1LBGd07oZCEMJLmEDSUMC3Wxmw81ZArrUzyEmozN9cYKD23ugMQZDZD'

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "NMN3005")
CSV_PATH = os.environ.get("CSV_PATH", "qna.csv")
MATCH_THRESHOLD = int(os.environ.get("MATCH_THRESHOLD", "80"))  # 0-100

app = Flask(__name__)

def normalize(text: str) -> str:
    if not text:
        return ""
    # Lowercase, remove accents, strip punctuation, collapse spaces
    t = unidecode(text.lower())
    t = t.translate(str.maketrans("", "", string.punctuation))
    t = " ".join(t.split())
    return t

def load_qna(csv_path: str):
    q_list, a_map = [], {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # Expect columns: Hoi, Tra_loi (Vietnamese headers with no spaces)
        # Also accept "Hỏi" and "Trả lời" with accents and spaces.
        # Normalize headers
        headers = [h.strip().lower() for h in reader.fieldnames]
        # Map possible header names
        def pick(colnames):
            alias = {
                "hoi": ["hoi", "hỏi", "question", "ask"],
                "traloi": ["tra_loi", "tra loi", "trả lời", "answer", "reply"]
            }
            for key, variants in alias.items():
                for v in variants:
                    if v in colnames:
                        yield key, v
                        break
        header_map = dict(pick(headers))
        q_col = header_map.get("hoi")
        a_col = header_map.get("traloi")
        if not (q_col and a_col):
            raise ValueError("CSV must include two columns for questions and answers. "
                             "Accepted headers include: Hoi/Hỏi/Question and Tra_loi/'Trả lời'/Answer.")
        for row in reader:
            q_raw = row.get(q_col, "").strip()
            a_raw = row.get(a_col, "").strip()
            if not q_raw:
                continue
            q_norm = normalize(q_raw)
            if q_norm:
                q_list.append(q_norm)
                a_map[q_norm] = a_raw
    if not q_list:
        raise ValueError("No Q&A pairs found in CSV.")
    return q_list, a_map

Q_INDEX, A_MAP = load_qna(CSV_PATH)

def best_answer(user_text: str):
    query = normalize(user_text)
    if not query:
        return None, 0
    best = process.extractOne(
        query, Q_INDEX, scorer=fuzz.token_set_ratio
    )
    if not best:
        return None, 0
    matched_q, score, _ = best  # matched_q is the normalized question
    if score >= MATCH_THRESHOLD:
        return A_MAP.get(matched_q, None), score
    return None, score

def send_message(recipient_id: str, text: str):
    if not PAGE_ACCESS_TOKEN:
        app.logger.error("PAGE_ACCESS_TOKEN is not set")
        return
    url = "https://graph.facebook.com/v18.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    r = requests.post(url, params=params, json=payload, timeout=10)
    if r.status_code >= 400:
        app.logger.error("FB send error: %s %s", r.status_code, r.text)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "q_count": len(Q_INDEX)})

@app.route("/webhook", methods=["GET"])
def verify():
    # Verification handshake
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification token mismatch", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True) or {}
    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event.get("sender", {}).get("id")
            if not sender_id:
                continue
            if "message" in event and "text" in event["message"]:
                user_text = event["message"]["text"]
                answer, score = best_answer(user_text)
                if answer:
                    send_message(sender_id, answer)
                else:
                    send_message(sender_id, "Xin lỗi, tôi chưa có câu trả lời phù hợp. "
                                            "Vui lòng đặt câu hỏi theo cách khác hoặc nhắn 'nhân viên' để gặp người hỗ trợ.")
            elif "postback" in event:
                payload = event["postback"].get("payload", "")
                if payload:
                    answer, score = best_answer(payload)
                    if answer:
                        send_message(sender_id, answer)
                    else:
                        send_message(sender_id, "Bạn cần hỗ trợ gì? Hãy nhập câu hỏi, ví dụ: 'giá', 'khuyến mãi', 'địa chỉ'.")
    return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)