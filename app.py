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

# Modes:
# coming
# draw
# live
# maintenance

# =========================================
# OPEN MIC SETTINGS
# =========================================

MAX_CHILDREN = 32

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

    # KARAOKE DRAW TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS karaoke_draw (
            singer TEXT UNIQUE,
            slots TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

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

def reset_openmic():

    conn = sqlite3.connect("database.db")

    cur = conn.cursor()

    cur.execute("DELETE FROM openmic")

    conn.commit()
    conn.close()

def reset_draw():

    conn = sqlite3.connect("database.db")

    cur = conn.cursor()

    cur.execute(
        "DELETE FROM karaoke_draw"
    )

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
# GET DRAW DATA
# =========================================

def get_draw_data():

    conn = sqlite3.connect("database.db")

    cur = conn.cursor()

    cur.execute(
        "SELECT singer, slots FROM karaoke_draw"
    )

    rows = cur.fetchall()

    conn.close()

    data = []

    for row in rows:

        data.append({

            "singer": row[0],

            "slots": list(
                map(int, row[1].split(","))
            )
        })

    return data

# =========================================
# DRAW SYSTEM
# =========================================

def assign_slots(singer):

    total_songs = SINGERS[singer]

    draw_data = get_draw_data()

    used_slots = []

    # GET USED SLOTS
    for item in draw_data:

        used_slots.extend(
            item["slots"]
        )

    # SLOT 1 RESERVED
    available = [

        x for x in range(
            1,
            TOTAL_SLOTS + 1
        )

        if x not in used_slots
        and x != 1
    ]

    # SINGLE SONG RULE
    if total_songs == 1:

        available = [

            x for x in available

            if x > 11
        ]

    random.shuffle(available)

    selected = []

    for slot in available:

        # PREVENT CLOSE SLOTS
        if any(

            abs(slot - s) <= 1

            for s in selected
        ):

            continue

        selected.append(slot)

        if len(selected) == total_songs:

            break

    if len(selected) != total_songs:

        return None, "Not enough slots"

    # SAVE IN DATABASE
    conn = sqlite3.connect("database.db")

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO karaoke_draw
        (singer, slots)
        VALUES (?, ?)
        """,
        (
            singer,
            ",".join(
                map(str, selected)
            )
        )
    )

    conn.commit()
    conn.close()

    return sorted(selected), None

# =========================================
# MAIN WEBSITE
# =========================================

@app.route("/", methods=["GET", "POST"])
def index():

    global MODE

    # =====================================
    # COMING SOON
    # =====================================

    if MODE == "coming":

        return render_template(
            "index.html"
        )

    # =====================================
    # DRAW MODE
    # =====================================

    elif MODE == "draw":

        result = None

        draw_data = get_draw_data()

        if request.method == "POST":

            singer = request.form.get(
                "singer"
            ).strip().lower()

            already_drawn = False

            for item in draw_data:

                if item["singer"] == singer:

                    already_drawn = True
                    result = item
                    break

            # NEW DRAW
            if not already_drawn:

                slots, error = assign_slots(
                    singer
                )

                if slots:

                    result = {

                        "singer": singer,
                        "slots": slots
                    }

                    send_telegram(
                        f"🎤 KARAOKE DRAW\n\n"
                        f"Singer: {singer.title()}\n"
                        f"Slots: {', '.join(map(str, slots))}"
                    )

            draw_data = get_draw_data()

        return render_template(

            "draw.html",

            singers=SINGERS.keys(),

            result=result,

            draw_data=draw_data
        )

    # =====================================
    # LIVE MODE
    # =====================================

    elif MODE == "live":

        return render_template(
            "live.html"
        )

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

    return render_template(
        "success.html"
    )

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

            # START DRAW
            if text == "/startdraw":

                MODE = "draw"

                send_telegram(
                    "🎤 Karaoke Draw Started"
                )

            # LIVE MODE
            elif text == "/live":

                MODE = "live"

                send_telegram(
                    "🔴 LIVE MODE ACTIVATED"
                )

            # COMING SOON
            elif text == "/end":

                MODE = "coming"

                send_telegram(
                    "⏹ Coming Soon Mode Activated"
                )

            # MAINTENANCE
            elif text == "/maintenance":

                MODE = "maintenance"

                send_telegram(
                    "⚙️ Maintenance Mode Activated"
                )

            # RESET DRAW
            elif text == "/reset":

                reset_draw()

                send_telegram(
                    "🔁 Karaoke Draw Reset"
                )

            # RESET OPENMIC
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
