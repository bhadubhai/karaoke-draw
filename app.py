from flask import Flask, render_template, request, redirect
import requests
import random
import os
import sqlite3

app = Flask(__name__)

# =========================================
# TELEGRAM CONFIG
# =========================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =========================================
# WEBSITE MODES
# =========================================

MODE = "coming"

# coming
# draw
# live
# maintenance

# =========================================
# OPEN MIC SETTINGS
# =========================================

MAX_CHILDREN = 32

# =========================================
# DATABASE
# =========================================

def init_db():

    conn = sqlite3.connect("database.db")

    cur = conn.cursor()

    # OPEN MIC TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS openmic (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================================
# KARAOKE SETTINGS
# =========================================

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

used_slots = []
draw_data = []

# =========================================
# TELEGRAM FUNCTION
# =========================================

def send_telegram(message):

    url = (
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    )

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        }
    )

# =========================================
# RESET FUNCTIONS
# =========================================

def reset_data():

    global used_slots
    global draw_data

    used_slots = []
    draw_data = []

def reset_openmic():

    conn = sqlite3.connect("database.db")

    cur = conn.cursor()

    cur.execute("DELETE FROM openmic")

    conn.commit()
    conn.close()

# =========================================
# OPENMIC COUNT
# =========================================

def get_total_openmic_registrations():

    conn = sqlite3.connect("database.db")

    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM openmic"
    )

    total = cur.fetchone()[0]

    conn.close()

    return total

# =========================================
# DRAW SYSTEM
# =========================================

def assign_slots(singer):

    global used_slots

    total_songs = SINGERS[singer]

    # Rule:
    # Slot 1 is reserved
    # Single-song singers get slot after 11

    available = [
        x for x in range(1, TOTAL_SLOTS + 1)
        if x not in used_slots and x != 1
    ]

    if total_songs == 1:
        available = [x for x in available if x > 11]

    random.shuffle(available)

    selected = []

    for slot in available:

        # Prevent nearby slots
        if any(abs(slot - s) <= 1 for s in selected):
            continue

        selected.append(slot)

        if len(selected) == total_songs:
            break

    if len(selected) != total_songs:

        return None, "Not enough slots"

    used_slots.extend(selected)

    return sorted(selected), None

# =========================================
# MAIN WEBSITE
# =========================================

@app.route("/", methods=["GET", "POST"])
def index():

    global MODE
    global draw_data

    # =====================================
    # COMING SOON
    # =====================================

    if MODE == "coming":

        return render_template("index.html")

    # =====================================
    # DRAW MODE
    # =====================================

   elif MODE == "draw":

    result = None

    if request.method == "POST":

        singer = (
            request.form.get("singer")
            .strip()
            .lower()
        )

        # Prevent redraw
        already_drawn = any(
            d["singer"] == singer
            for d in draw_data
        )

        if not already_drawn:

            slots, error = assign_slots(singer)

            if slots:

                result = {
                    "singer": singer,
                    "slots": slots
                }

                draw_data.append(result)

                # TELEGRAM MESSAGE
                send_telegram(
                    f"🎤 KARAOKE DRAW\n\n"
                    f"Singer: {singer.title()}\n"
                    f"Slots: {', '.join(map(str, slots))}"
                )

    return render_template(
        "draw.html",
        singers=SINGERS.keys(),
        result=result
    )
    # =====================================
    # LIVE MODE
    # =====================================

    elif MODE == "live":

        return render_template("live.html")

    # =====================================
    # MAINTENANCE MODE
    # =====================================

    elif MODE == "maintenance":

        return render_template(
            "maintenance.html"
        )

# =========================================
# OPEN MIC PAGE
# =========================================

@app.route("/openmic", methods=["GET", "POST"])
def openmic():

    total = get_total_openmic_registrations()

    # REGISTRATION CLOSED
    if total >= MAX_CHILDREN:

        return (
            "🎤 Open Mic Registrations Closed"
        )

    if request.method == "POST":

        name = request.form.get("name")
        age = request.form.get("age")
        parent = request.form.get("parent")
        mobile = request.form.get("mobile")
        performance = request.form.get("performance")

        # AGE VALIDATION
        if int(age) > 15:

            return (
                "Only children up to 15 years allowed"
            )

        # TELEGRAM MESSAGE
        send_telegram(
            f"🎉 OPEN MIC REGISTRATION\n\n"
            f"Child: {name}\n"
            f"Age: {age}\n"
            f"Parent: {parent}\n"
            f"Mobile: {mobile}\n"
            f"Performance: {performance}\n"
            f"Payment: ₹100 Pending\n\n"
            f"Venue: Evening Post, Kasturba Road, Rajkot"
        )

        # PAYMENT PAGE
        return redirect(
            "https://rzp.io/rzp/uUJzXQp"
        )

    remaining = MAX_CHILDREN - total

    return render_template(
        "openmic.html",
        remaining=remaining
    )

# =========================================
# PAYMENT SUCCESS
# =========================================

@app.route("/success")
def success():

    conn = sqlite3.connect("database.db")

    cur = conn.cursor()

    cur.execute(
        "INSERT INTO openmic DEFAULT VALUES"
    )

    conn.commit()
    conn.close()

    return render_template("success.html")

# =========================================
# TELEGRAM WEBHOOK
# =========================================

@app.route("/telegram", methods=["POST"])
def telegram_webhook():

    global MODE

    data = request.json

    try:

        if "message" in data:

            message = data["message"]

            text = (
                message.get("text", "")
                .strip()
                .lower()
            )

            chat_id = str(
                message["chat"]["id"]
            )

            # SECURITY
            if chat_id != str(CHAT_ID):

                return "Unauthorized"

            # =================================
            # START DRAW
            # =================================

            if text == "/startdraw":

                MODE = "draw"

                send_telegram(
                    "🎤 Karaoke Draw Started"
                )

            # =================================
            # LIVE MODE
            # =================================

            elif text == "/live":

                MODE = "live"

                send_telegram(
                    "🔴 LIVE MODE ACTIVATED"
                )

            # =================================
            # COMING SOON
            # =================================

            elif text == "/end":

                MODE = "coming"

                send_telegram(
                    "⏹ Coming Soon Mode Activated"
                )

            # =================================
            # MAINTENANCE
            # =================================

            elif text == "/maintenance":

                MODE = "maintenance"

                send_telegram(
                    "⚙️ Maintenance Mode Activated"
                )

            # =================================
            # RESET DRAW
            # =================================

            elif text == "/reset":

                reset_data()

                send_telegram(
                    "🔁 Karaoke Draw Reset"
                )

            # =================================
            # RESET OPENMIC
            # =================================

            elif text == "/resetopenmic":

                reset_openmic()

                send_telegram(
                    "🎤 Open Mic Reset Successful\n\n"
                    "32 Slots Reopened ✅"
                )

    except Exception as e:

        print("ERROR:", e)

    return "ok"

# =========================================
# RUN APP
# =========================================

if __name__ == "__main__":

    app.run(debug=True)
