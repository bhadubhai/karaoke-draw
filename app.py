# WEBSITE MODES

MODE = "coming"

# coming
# draw
# live
# maintenance
from flask import Flask, render_template, request, redirect
import sqlite3
import random
import requests
import os

app = Flask(__name__)

# 🔐 ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1111")

# 🎤 DRAW STATUS
DRAW_STARTED = False

# 🎵 SINGERS
SINGERS = {
    "chetanbhai pandya": 6,
    "chandreshbhai fichadiya": 6,
    "anilbhai mavadiya": 3,
    "jiteshbhai jivrajani": 3,
    "kamleshbhai dave": 2,
    "pareshbhai khakhkhar": 2,
    "narendrabhai khakhkhar": 1,
    "jaysukhbhai parekh": 1,
    "rockstar": 3,
    "jagdishbhai kariya": 2,
    "ashokbhai dhamecha": 1,
}

TOTAL_SLOTS = 31


# 📁 DB INIT
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
        c.execute(
            "INSERT INTO draws VALUES (?, ?)",
            (name, slot)
        )

    conn.commit()
    conn.close()


# 🔁 RESET
def reset_data():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("DELETE FROM draws")

    conn.commit()
    conn.close()


# 📤 TELEGRAM
def send_telegram(msg):

    if not BOT_TOKEN or not CHAT_ID:
        print("Missing Telegram config")
        return

    try:

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        })

    except Exception as e:
        print("Telegram Error:", e)


# 🎲 RANDOM SLOT ASSIGNMENT
def assign_slots(singer):

    data = get_data()

    used = {d["slot"] for d in data}

    existing = [
        d["slot"] for d in data
        if d["name"] == singer
    ]

    if existing:
        return None, f"Already assigned: {sorted(existing)}"

    total = SINGERS[singer]

    available = [
        s for s in range(1, TOTAL_SLOTS + 1)
        if s not in used
    ]

    for _ in range(700):

        if len(available) < total:
            break

        sample = sorted(random.sample(available, total))

        block_count = {}
        valid = True

        for s in sample:

            block = (s - 1) // 10

            max_per_block = 2 if total == 6 else 1

            block_count[block] = block_count.get(block, 0) + 1

            if block_count[block] > max_per_block:
                valid = False
                break

        # ❌ no consecutive
        if valid:
            for i in range(len(sample)-1):

                if abs(sample[i] - sample[i+1]) <= 1:
                    valid = False
                    break

        if valid:
            return sample, None

    return None, "No valid slots available"


# 🌐 MAIN WEBSITE
@app.route("/", methods=["GET", "POST"])
def index():

    global MODE

    init_db()
        # ⚙️ MAINTENANCE PAGE
    elif MODE == "maintenance":
        return render_template("maintenance.html")

    # 🚀 COMING SOON
    if MODE == "coming":
        return render_template("index.html")

    # 🎤 DRAW SYSTEM
    elif MODE == "draw":

        result = None

        data = sorted(
            get_data(),
            key=lambda x: x["slot"]
        )

        if request.method == "POST":

            singer = request.form.get("name")

            if singer:

                slots, error = assign_slots(singer)

                if error:
                    result = error

                else:

                    save_data(singer, slots)

                    result = f"{singer} → {slots}"

                    send_telegram(
                        f"🎤 Karaoke Draw\n\nSinger: {singer}\nSlots: {slots}"
                    )

        return render_template(
            "draw.html",
            singers=SINGERS,
            data=data,
            result=result
        )

    # 🔴 LIVE PAGE
    elif MODE == "live":
        return render_template("live.html")

    # 🚫 COMING SOON PAGE
    if not DRAW_STARTED:
        return render_template("index.html")

    # 🎤 DRAW SYSTEM PAGE
    result = None

    data = sorted(
        get_data(),
        key=lambda x: x["slot"]
    )

    if request.method == "POST":

        singer = request.form.get("name")

        if singer:

            slots, error = assign_slots(singer)

            if error:
                result = error

            else:

                save_data(singer, slots)

                result = f"{singer} → {slots}"

                send_telegram(
                    f"🎤 Karaoke Draw\n\nSinger: {singer}\nSlots: {slots}"
                )

    return render_template(
        "draw.html",
        singers=SINGERS,
        data=data,
        result=result
    )


# 🤖 TELEGRAM CONTROL
@app.route("/telegram", methods=["POST"])
def telegram_webhook():

    global MODE

    data = request.json

    print(data)

    try:

        if "message" in data:

            message = data["message"]

            text = message.get("text", "").strip()

            chat_id = str(message["chat"]["id"])

            # 🔐 ADMIN CHECK
            if chat_id != str(CHAT_ID):
                return "Unauthorized"

            # 🎤 DRAW MODE
            if text == "/startdraw":

                MODE = "draw"

                send_telegram(
                    "🎤 Karaoke Draw STARTED"
                )

            # 🔴 LIVE MODE
            elif text == "/live":

                MODE = "live"

                send_telegram(
                    "🔴 LIVE MODE ACTIVATED"
                )

            # ⏹ END EVENT
            elif text == "/end":

                MODE = "coming"

                send_telegram(
                    "⏹ Event Ended\n\nComing Soon Page Activated"
                )

            # 🔁 RESET
            elif text == "/reset":

                reset_data()

                send_telegram(
                    "⚠️ Karaoke Draw Reset"
                )

            # ⚙️ MAINTENANCE MODE
            elif text == "/maintenance":

                MODE = "maintenance"

                send_telegram(
                    "⚙️ Maintenance Mode Activated"
                )
    except Exception as e:

        print(e)

    return "ok"
