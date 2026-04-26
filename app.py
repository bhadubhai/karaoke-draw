from flask import Flask, render_template, request, redirect
import sqlite3
import random
import requests


app = Flask(__name__)

BOT_TOKEN = "..."

SINGERS = {
    "chetanbhai pandya": 6,
    "chandreshbhai fichadiya": 1,
    "anilbhai mavadiya": 3,
    "jiteshbhai jivrajani": 3,
    "kamleshbhai dave": 3,
    "pareshbhai khakhkhar": 3,
    "narendrabhai khakhkhar": 2,
    "jaysukhbhai parekh": 2,
    "rockstar": 2,
    "jagdishbhai kariya": 2,
    "ashokbhai dhamecha": 2,
    "naynaben vyas ": 2,
}

TOTAL_SLOTS = 31

CHAT_ID = "..."  # will be auto filled


# 📁 DB
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS draws (singer TEXT, slot INTEGER)")
    conn.commit()
    conn.close()


def get_data():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT singer, slot FROM draws")
    rows = c.fetchall()
    conn.close()
    return [{"name": r[0], "slot": r[1]} for r in rows]


def save_data(name, slots):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    for slot in slots:
        c.execute("INSERT INTO draws VALUES (?, ?)", (name, slot))
    conn.commit()
    conn.close()


def reset_data():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("DELETE FROM draws")
    conn.commit()
    conn.close()


# 📤 TELEGRAM SEND
def send_telegram(msg):
    global CHAT_ID
    if not CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})


# 🎲 ASSIGN
def assign_slots(singer):
    data = get_data()
    used = {d["slot"] for d in data}

    existing = [d["slot"] for d in data if d["name"] == singer]
    if existing:
        return None, f"Already assigned: {sorted(existing)}"

    total = SINGERS[singer]
    available = [s for s in range(1, TOTAL_SLOTS + 1) if s not in used]

    for _ in range(500):
        if len(available) < total:
            break

        sample = sorted(random.sample(available, total))

        block = {}
        valid = True

        for s in sample:
            b = (s - 1) // 10
            limit = 2 if total == 6 else 1
            block[b] = block.get(b, 0) + 1
            if block[b] > limit:
                valid = False
                break

        for i in range(len(sample)-1):
            if abs(sample[i] - sample[i+1]) <= 1:
                valid = False

        if valid:
            return sample, None

    return None, "No valid slots"


# 🌐 WEBSITE
@app.route("/", methods=["GET", "POST"])
def index():
    init_db()
    data = sorted(get_data(), key=lambda x: x["slot"])
    result = None

    if request.method == "POST":
        singer = request.form.get("name")

        slots, error = assign_slots(singer)

        if error:
            result = error
        else:
            save_data(singer, slots)
            result = f"{singer} → {slots}"

            send_telegram(f"🎤 {singer}\nSlots: {slots}")

    return render_template("index.html", singers=SINGERS, data=data, result=result)


# 🔁 RESET
@app.route("/reset", methods=["POST"])
def reset():
    if request.form.get("password") == ADMIN_PASSWORD:
        reset_data()
        send_telegram("⚠️ RESET DONE")
    return redirect("/")


# 🤖 TELEGRAM WEBHOOK
@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    global CHAT_ID

    data = request.json

    if "message" in data:
        msg = data["message"]
        CHAT_ID = msg["chat"]["id"]
        text = msg.get("text", "")

        # ADMIN COMMANDS
        if text == "/start":
            send_telegram("✅ Bot connected!")

        elif text == "/reset":
            reset_data()
            send_telegram("⚠️ System Reset via Telegram")

        elif text == "/status":
            all_data = get_data()
            msg = "\n".join([f"{d['name']} → {d['slot']}" for d in all_data])
            send_telegram("📊 Current Data:\n" + msg)

    return "ok"


if __name__ == "__main__":
    app.run()