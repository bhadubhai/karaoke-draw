from flask import Flask, render_template, request, redirect
import requests
import random
import os
import sqlite3

app = Flask(__name__)

# =========================================
# DATABASE PATH
# =========================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_PATH = os.path.join(
    BASE_DIR,
    "database.db"
)

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

     "chetanbhai ": 4,
    "Amrish bhai": 3,
    "anilbhai ": 2,
    "etubhai": 3,
    "Kashmiraben": 1,
    "Kishor sinh": 2,
    "Maheshbhai": 2,
    "Ntinbhai": 2,
    "pareshbhai": 3,
    "jagdishbhai": 1,
    "shaistaben": 1,
    "Falgun bhai ": 1,
    "Rajendrabhai ": 1, 
    "sonalben ": 1,
    "narendrabhai": 1,
    "yog bhai": 1, 
    "zala bhai ": 1,
    "jyotiben ": 1
    "prakash bhai ": 2
}

TOTAL_SLOTS = 40

# =========================================
# DATABASE INIT
# =========================================

def init_db():

    conn = sqlite3.connect(DB_PATH)

    cur = conn.cursor()

    # OPENMIC TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS openmic (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        )
    """)

    # DRAW TABLE
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

    try:

        url = (
            f"https://api.telegram.org/"
            f"bot{BOT_TOKEN}/sendMessage"
        )

        requests.post(

            url,

            data={

                "chat_id": CHAT_ID,
                "text": message
            }
        )

    except Exception as e:

        print("Telegram Error:", e)

# =========================================
# RESET FUNCTIONS
# =========================================

def reset_openmic():

    conn = sqlite3.connect(DB_PATH)

    cur = conn.cursor()

    cur.execute(
        "DELETE FROM openmic"
    )

    conn.commit()
    conn.close()

def reset_draw():

    conn = sqlite3.connect(DB_PATH)

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

    conn = sqlite3.connect(DB_PATH)

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

    conn = sqlite3.connect(DB_PATH)

    cur = conn.cursor()

    cur.execute(
        """
        SELECT singer, slots
        FROM karaoke_draw
        ORDER BY rowid ASC
        """
    )

    rows = cur.fetchall()

    conn.close()

    data = []

    for singer, slots in rows:

        data.append({

            "singer": singer,

            "slots": [

                int(x)

                for x in slots.split(",")

                if x.strip()
            ]
        })

    return data

# =========================================
# ADVANCED SMART DRAW SYSTEM
# =========================================

def assign_slots(singer):

    total_songs = SINGERS[singer]

    draw_data = get_draw_data()

    used_slots = set()

    # =====================================
    # RESERVED SLOTS
    # =====================================

    RESERVED_SLOTS = [
        1,
        8,
        13,
        15,
        18,
        25,
        40
    ]

    # =====================================
    # GET USED SLOTS
    # =====================================

    for item in draw_data:

        for slot in item["slots"]:

            used_slots.add(slot)

    # ADD RESERVED SLOTS
    for r in RESERVED_SLOTS:

        used_slots.add(r)

    selected = []

    # =====================================
    # RANDOM SLOT FUNCTION
    # =====================================

    def get_random_slot(start, end):

        available = [

            x for x in range(start, end + 1)

            if x not in used_slots
            and x not in selected
        ]

        random.shuffle(available)

        for slot in available:

            # PREVENT CLOSE NUMBERS
            invalid = False

            for s in selected:

                if abs(slot - s) <= 1:

                    invalid = True
                    break

            if not invalid:

                return slot

        return None

    # =====================================
    # 1 SONG
    # (11-17) OR (27-32)
    # =====================================

    if total_songs == 1:

        ranges = [

            (11, 17),
            (27, 32)
        ]

        random.shuffle(ranges)

        for start, end in ranges:

            slot = get_random_slot(
                start,
                end
            )

            if slot:

                selected.append(slot)
                break

    # =====================================
    # 2 SONGS
    # FIRST: 2-12
    # SECOND: 20-30
    # =====================================

    elif total_songs == 2:

        first = get_random_slot(2, 12)

        if first:

            selected.append(first)

        second = get_random_slot(20, 30)

        if second:

            selected.append(second)

    # =====================================
    # 3 SONGS
    # 2-10
    # 11-20
    # 31-35
    # =====================================

    elif total_songs == 3:

        ranges = [

            (2, 10),
            (11, 20),
            (31, 35)
        ]

        for start, end in ranges:

            slot = get_random_slot(
                start,
                end
            )

            if slot:

                selected.append(slot)

    # =====================================
    # 4 SONGS
    # 1-10
    # 10-20
    # 20-30
    # 30-39
    # =====================================

    elif total_songs == 4:

        ranges = [

            (1, 10),
            (10, 20),
            (20, 30),
            (30, 39)
        ]

        for start, end in ranges:

            slot = get_random_slot(
                start,
                end
            )

            if slot:

                selected.append(slot)

    # =====================================
    # EXTRA SONGS > 4
    # =====================================

    else:

        while len(selected) < total_songs:

            slot = get_random_slot(
                1,
                TOTAL_SLOTS
            )

            if not slot:
                break

            selected.append(slot)

    # =====================================
    # VALIDATION
    # =====================================

    if len(selected) != total_songs:

        return None, "Not enough slots"

    selected = sorted(selected)

    # =====================================
    # SAVE DATABASE
    # =====================================

    conn = sqlite3.connect(DB_PATH)

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

    return selected, None
    
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

        draw_data = get_draw_data()

        result = None

        # HANDLE DRAW
        if (
            request.method == "POST"
            and request.form.get("singer")
        ):

            singer = (
                request.form.get("singer")
                .strip()
                .lower()
            )

            # ALREADY DRAWN
            for item in draw_data:

                if item["singer"] == singer:

                    return redirect(
                        "/?already=1"
                    )

            # NEW DRAW
            slots, error = assign_slots(
                singer
            )

            if slots:

                send_telegram(
                    f"🎤 KARAOKE DRAW\n\n"
                    f"Singer: {singer.title()}\n"
                    f"Slots: {', '.join(map(str, slots))}"
                )

                return redirect(
                    f"/?singer={singer}"
                )

        # SHOW RESULT
        singer_name = request.args.get(
            "singer"
        )

        if singer_name:

            draw_data = get_draw_data()

            for item in draw_data:

                if item["singer"] == singer_name:

                    result = item
                    break

        return render_template(

            "draw.html",

            singers=SINGERS.keys(),

            result=result,

            draw_data=get_draw_data()
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
# OPENMIC PAGE
# =========================================

@app.route("/openmic", methods=["GET", "POST"])
def openmic():

    total = get_total_openmic_registrations()

    # CLOSED
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

        # AGE CHECK
        if int(age) > 15:

            return (
                "Only children up to 15 years allowed"
            )

        # TELEGRAM
        send_telegram(

            f"🎉 OPEN MIC REGISTRATION\n\n"

            f"Child: {name}\n"

            f"Age: {age}\n"

            f"Parent: {parent}\n"

            f"Mobile: {mobile}\n"

            f"Performance: {performance}\n"

            f"Payment: ₹100 Pending\n\n"

            f"Venue: Evening Post, Rajkot"
        )

        # PAYMENT
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

    conn = sqlite3.connect(DB_PATH)

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
# DEBUG ROUTE
# =========================================

@app.route("/debug")
def debug():

    return {

        "mode": MODE,

        "draw_data": get_draw_data()
    }

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

        print("Webhook Error:", e)

    return "ok"

# =========================================
# RUN APP
# =========================================

if __name__ == "__main__":

    app.run(debug=True)
