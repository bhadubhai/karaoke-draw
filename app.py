from flask import Flask, render_template, request, redirect
import sqlite3
import random
import requests
import os

app = Flask(__name__)

# 🔐 ENV VARIABLES (from Render)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# 🎤 Singer setup
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
    "naynaben vyas ": 2
}

TOTAL_SLOTS = 31


# 📁 INIT DB
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS draws (
            singer TEXT,
            slot INTEGER
        )
    """)
    conn.commit()
    conn.close()


# 📊 GET DATA
def get_data():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT singer, slot FROM draws")
    rows = c.fetchall()
    conn.close()
    return [{"name": r[0], "slot": r[1]} for r in rows]


# 💾 SAVE DATA
def save_data(name, slots):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    for slot in slots:
        c.execute("INSERT INTO draws VALUES (?, ?)", (name, slot))
    conn.commit()
    conn.close()


# 🔁 RESET DATA
def reset_data():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("DELETE FROM draws")
    conn.commit()
    conn.close()


# 📤 TELEGRAM SEND (SAFE)
def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram not configured")
        return

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        })
    except Exception as e:
        print("Telegram error:", e)


# 🎲 RANDOM SLOT ASSIGNMENT
def assign_slots(singer):
    data = get_data()
    used = {d["slot"] for d in data}

    # ❌ already assigned
    existing = [d["slot"] for d in data if d["name"] == singer]
    if existing:
        return None, f"Already assigned: {sorted(existing)}"

    total = SINGERS[singer]
    available = [s for s in range(1, TOTAL_SLOTS + 1) if s not in used]

    for _ in range(700):
        if len(available) < total:
            break

        sample = sorted(random.sample(available, total))

        # block rule
        block_count = {}
        valid = True

        for s in sample:
            block = (s - 1) // 10
            max_per_block = 2 if total == 6 else 1

            block_count[block] = block_count.get(block, 0) + 1
            if block_count[block] > max_per_block:
                valid = False
                break

        # spacing rule (no consecutive)
        if valid:
            for i in range(len(sample) - 1):
                if abs(sample[i] - sample[i + 1]) <= 1:
                    valid = False
                    break

        if valid:
            return sample, None

    return None, "No valid slots available"


# 🌐 MAIN ROUTE
@app.route("/", methods=["GET", "POST"])
def index():
    init_db()

    result = None
    data = sorted(get_data(), key=lambda x: x["slot"])

    if request.method == "POST":
        singer = request.form.get("name")

        if singer:
            slots, error = assign_slots(singer)

            if error:
                result = f"{singer}: {error}"
            else:
                save_data(singer, slots)
                result = f"{singer} → {slots}"

                # 📤 SEND TO TELEGRAM
                msg = f"🎤 Karaoke Draw\n\nSinger: {singer}\nSlots: {', '.join(map(str, slots))}"
                send_telegram(msg)

    return render_template("index.html", singers=SINGERS, data=data, result=result)


# 🔁 RESET ROUTE
@app.route("/reset", methods=["POST"])
def reset():
    password = request.form.get("password", "").strip()

    print("RAW INPUT:", repr(password))
    print("EXPECTED:", repr(ADMIN_PASSWORD))

    if password == ADMIN_PASSWORD:
        print("✅ RESET SUCCESS")

        reset_data()

        try:
            send_telegram("⚠️ Karaoke system RESET")
        except Exception as e:
            print("Telegram error:", e)

        return redirect("/")

    print("❌ WRONG PASSWORD")
    return redirect("/")
