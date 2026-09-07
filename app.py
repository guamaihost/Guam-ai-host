import os

import json

import sqlite3

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from urllib.parse import urlparse

HOST = "0.0.0.0"

PORT = int(os.environ.get("PORT", "8000"))

DB_FILE = "guam_host_v4.db"

STATIC_DIR = "static"

# ---------------------------------------------------------

# DATABASE

# ---------------------------------------------------------

def get_db():

    conn = sqlite3.connect(DB_FILE)

    conn.row_factory = sqlite3.Row

    return conn

def init_db():

    conn = get_db()

    conn.execute("""

        CREATE TABLE IF NOT EXISTS experiences (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            business TEXT NOT NULL,

            category TEXT NOT NULL,

            price REAL NOT NULL,

            start_time TEXT NOT NULL,

            duration_minutes INTEGER NOT NULL,

            spots INTEGER NOT NULL,

            location TEXT NOT NULL,

            description TEXT DEFAULT ''

        )

    """)

    conn.execute("""

        CREATE TABLE IF NOT EXISTS travelers (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT DEFAULT '',

            language TEXT DEFAULT 'English'

        )

    """)

    conn.execute("""

        CREATE TABLE IF NOT EXISTS bookings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            booking_code TEXT UNIQUE NOT NULL,

            experience_id INTEGER NOT NULL,

            traveler_name TEXT NOT NULL,

            traveler_email TEXT DEFAULT '',

            language TEXT DEFAULT 'English',

            quantity INTEGER NOT NULL,

            total REAL NOT NULL,

            status TEXT DEFAULT 'confirmed',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (experience_id) REFERENCES experiences(id)

        )

    """)

    conn.commit()

    conn.close()

def seed():

    conn = get_db()

    count = conn.execute(

        "SELECT COUNT(*) AS count FROM experiences"

    ).fetchone()["count"]

    if count == 0:

        experiences = [

            (

                "Sunset Beach Escape",

                "Tumon Sunset Tours",

                "beach",

                59,

                "2026-09-07 16:15",

                90,

                8,

                "Tumon",

                "Relax on Guam's coast and enjoy a beautiful sunset."

            ),

            (

                "Guam Food & Shopping Night",

                "Island Food Co.",

                "food",

                42,

                "2026-09-07 18:00",

                120,

                12,

                "Tumon",

                "Local food, shopping and an easy evening experience."

            ),

            (

                "Ocean Adventure",

                "Guam Ocean Club",

                "ocean",

                75,

                "2026-09-07 13:30",

                150,

                6,

                "Hagåtña",

                "A fun ocean experience for travelers looking for adventure."

            ),

            (

                "Island Reset Spa",

                "Island Reset Spa",

                "wellness",

                69,

                "2026-09-07 15:30",

                90,

                3,

                "Tumon",

                "Relax and recharge with a Guam wellness experience."

            ),

            (

                "Guam Couple Photo Walk",

                "Guam Photo Co.",

                "photo",

                99,

                "2026-09-07 17:00",

                75,

                2,

                "Two Lovers Point",

                "A private photo walk for couples and special trips."

            ),

            (

                "Secret Beach Picnic",

                "Local Guam Experiences",

                "beach",

                79,

                "2026-09-07 11:00",

                120,

                4,

                "West Guam",

                "A relaxed private picnic experience away from the crowds."

            )

        ]

        conn.executemany("""

            INSERT INTO experiences

            (

                title,

                business,

                category,

                price,

                start_time,

                duration_minutes,

                spots,

                location,

                description

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

        """, experiences)

        conn.commit()

    conn.close()

# ---------------------------------------------------------

# HELPERS

# ---------------------------------------------------------

def json_response(handler, data, status=200):

    body = json.dumps(

        data,

        ensure_ascii=False

    ).encode("utf-8")

    handler.send_response(status)

    handler.send_header("Content-Type", "application/json; charset=utf-8")

    handler.send_header("Content-Length", str(len(body)))

    handler.send_header("Access-Control-Allow-Origin", "*")

    handler.end_headers()

    handler.wfile.write(body)

def read_json(handler):

    try:

        length = int(handler.headers.get("Content-Length", "0"))

        raw = handler.rfile.read(length)

        if not raw:

            return {}

        return json.loads(raw.decode("utf-8"))

    except Exception:

        return {}

def make_booking_code():

    import random

    import string

    letters = string.ascii_uppercase + string.digits

    return "GUAM-" + "".join(

        random.choice(letters) for _ in range(6)

    )

def row_to_dict(row):

    return dict(row)

# ---------------------------------------------------------

# RECOMMENDATION ENGINE

# ---------------------------------------------------------

def recommend_experiences(message, budget=None):

    conn = get_db()

    rows = conn.execute("""

        SELECT *

        FROM experiences

        WHERE spots > 0

        ORDER BY start_time

    """).fetchall()

    conn.close()

    text = (message or "").lower()

    scored = []

    keyword_map = {

        "beach": ["beach", "ocean", "sunset", "海", "ビーチ", "바다", "해변"],

        "food": ["food", "eat", "restaurant", "shopping", "食", "グルメ", "맛집", "쇼핑"],

        "ocean": ["ocean", "water", "adventure", "snorkel", "海", "アクティビティ", "바다"],

        "wellness": ["spa", "relax", "wellness", "massage", "スパ", "휴식", "스파"],

        "photo": ["photo", "couple", "romantic", "사진", "写真", "커플"],

    }

    for row in rows:

        score = 0

        category = row["category"]

        if category in keyword_map:

            for keyword in keyword_map[category]:

                if keyword in text:

                    score += 3

        if "cheap" in text or "budget" in text or "저렴" in text or "安い" in text:

            if row["price"] <= 60:

                score += 2

        if "romantic" in text or "couple" in text or "date" in text:

            if category == "photo":

                score += 5

        if "relax" in text or "relaxing" in text:

            if category == "wellness":

                score += 5

        if "food" in text or "eat" in text or "dinner" in text:

            if category == "food":

                score += 5

        if "beach" in text or "sunset" in text:

            if category == "beach":

                score += 5

        if "adventure" in text or "ocean" in text:

            if category == "ocean":

                score += 5

        if budget is not None:

            try:

                if float(row["price"]) <= float(budget):

                    score += 2

                else:

                    score -= 2

            except Exception:

                pass

        scored.append((score, row))

    scored.sort(

        key=lambda item: (

            -item[0],

            item[1]["price"]

        )

    )

    return [

        row_to_dict(row)

        for score, row in scored[:5]

    ]

# ---------------------------------------------------------

# HTTP HANDLER

# ---------------------------------------------------------

class GuamAIHostHandler(BaseHTTPRequestHandler):

    def send_cors(self):

        self.send_header(

            "Access-Control-Allow-Origin",

            "*"

        )

        self.send_header(

            "Access-Control-Allow-Headers",

            "Content-Type"

        )

        self.send_header(

            "Access-Control-Allow-Methods",

            "GET, POST, OPTIONS"

        )

    def do_OPTIONS(self):

        self.send_response(204)

        self.send_cors()

        self.end_headers()

    def do_GET(self):

        parsed = urlparse(self.path)

        path = parsed.path

        if path == "/api/health":

            json_response(

                self,

                {

                    "status": "ok",

                    "service": "Guam AI Host",

                    "version": "V4"

                }

            )

            return

        if path == "/api/experiences":

            self.get_experiences()

            return

        if path == "/api/businesses":

            self.get_businesses()

            return

        if path == "/api/bookings":

            self.get_bookings()

            return

        if path == "/api/stats":

            self.get_stats()

            return

        self.serve_static(path)

    def do_POST(self):

        parsed = urlparse(self.path)

        path = parsed.path

        if path == "/api/recommend":

            self.recommend()

            return

        if path == "/api/experiences":

            self.create_experience()

            return

        if path == "/api/bookings":

            self.create_booking()

            return

        json_response(

            self,

            {"error": "Not found"},

            404

        )

    # -----------------------------------------------------

    # API: EXPERIENCES

    # -----------------------------------------------------

    def get_experiences(self):

        conn = get_db()

        rows = conn.execute("""

            SELECT *

            FROM experiences

            ORDER BY start_time

        """).fetchall()

        conn.close()

        json_response(

            self,

            [row_to_dict(row) for row in rows]

        )

    # -----------------------------------------------------

    # API: BUSINESSES

    # -----------------------------------------------------

    def get_businesses(self):

        conn = get_db()

        rows = conn.execute("""

            SELECT

                business,

                COUNT(*) AS experiences,

                SUM(spots) AS available_spots

            FROM experiences

            GROUP BY business

            ORDER BY business

        """).fetchall()

        conn.close()

        json_response(

            self,

            [row_to_dict(row) for row in rows]

        )

    # -----------------------------------------------------

    # API: BOOKINGS

    # -----------------------------------------------------

    def get_bookings(self):

        conn = get_db()

        rows = conn.execute("""

            SELECT

                bookings.*,

                experiences.title,

                experiences.business

            FROM bookings

            JOIN experiences

                ON experiences.id = bookings.experience_id

            ORDER BY bookings.created_at DESC

        """).fetchall()

        conn.close()

        json_response(

            self,

            [row_to_dict(row) for row in rows]

        )

    # -----------------------------------------------------

    # API: STATS

    # -----------------------------------------------------

    def get_stats(self):

        conn = get_db()

        travelers = conn.execute("""

            SELECT COUNT(DISTINCT traveler_email)

            FROM bookings

            WHERE traveler_email != ''

        """).fetchone()[0]

        bookings = conn.execute("""

            SELECT COUNT(*)

            FROM bookings

        """).fetchone()[0]

        gmv = conn.execute("""

            SELECT COALESCE(SUM(total), 0)

            FROM bookings

            WHERE status = 'confirmed'

        """).fetchone()[0]

        businesses = conn.execute("""

            SELECT COUNT(DISTINCT business)

            FROM experiences

        """).fetchone()[0]

        available_spots = conn.execute("""

            SELECT COALESCE(SUM(spots), 0)

            FROM experiences

        """).fetchone()[0]

        conn.close()

        json_response(

            self,

            {

                "travelers": travelers,

                "bookings": bookings,

                "gmv": round(float(gmv), 2),

                "businesses": businesses,

                "available_spots": available_spots

            }

        )

    # -----------------------------------------------------

    # API: RECOMMEND

    # -----------------------------------------------------

    def recommend(self):

        data = read_json(self)

        message = data.get(

            "message",

            ""

        )

        budget = data.get(

            "budget"

        )

        recommendations = recommend_experiences(

            message,

            budget

        )

        json_response(

            self,

            {

                "message": message,

                "recommendations": recommendations

            }

        )

    # -----------------------------------------------------

    # API: CREATE EXPERIENCE

    # -----------------------------------------------------

    def create_experience(self):

        data = read_json(self)

        required = [

            "title",

            "business",

            "category",

            "price",

            "start_time",

            "duration_minutes",

            "spots",

            "location"

        ]

        missing = [

            field

            for field in required

            if field not in data

        ]

        if missing:

            json_response(

                self,

                {

                    "error": "Missing fields",

                    "fields": missing

                },

                400

            )

            return

        try:

            price = float(data["price"])

            duration = int(data["duration_minutes"])

            spots = int(data["spots"])

            if price < 0 or duration <= 0 or spots <= 0:

                raise ValueError()

        except Exception:

            json_response(

                self,

                {

                    "error": "Invalid price, duration, or spots"

                },

                400

            )

            return

        conn = get_db()

        cursor = conn.execute("""

            INSERT INTO experiences

            (

                title,

                business,

                category,

                price,

                start_time,

                duration_minutes,

                spots,

                location,

                description

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

        """, (

            str(data["title"]),

            str(data["business"]),

            str(data["category"]),

            price,

            str(data["start_time"]),

            duration,

            spots,

            str(data["location"]),

            str(data.get("description", ""))

        ))

        conn.commit()

        experience_id = cursor.lastrowid

        row = conn.execute("""

            SELECT *

            FROM experiences

            WHERE id = ?

        """, (experience_id,)).fetchone()

        conn.close()

        json_response(

            self,

            row_to_dict(row),

            201

        )

    # -----------------------------------------------------

    # API: CREATE BOOKING

    # -----------------------------------------------------

    def create_booking(self):

        data = read_json(self)

        try:

            experience_id = int(

                data["experience_id"]

            )

            quantity = int(

                data.get("quantity", 1)

            )

            traveler_name = str(

                data.get(

                    "traveler_name",

                    "Guest"

                )

            )

            traveler_email = str(

                data.get(

                    "traveler_email",

                    ""

                )

            )

            language = str(

                data.get(

                    "language",

                    "English"

                )

            )

            if quantity <= 0:

                raise ValueError()

        except Exception:

            json_response(

                self,

                {

                    "error": "Invalid booking information"

                },

                400

            )

            return

        conn = get_db()

        try:

            # Prevent two simultaneous bookings

            # from overselling the same inventory.

            conn.execute("BEGIN IMMEDIATE")

            experience = conn.execute("""

                SELECT *

                FROM experiences

                WHERE id = ?

            """, (experience_id,)).fetchone()

            if experience is None:

                conn.rollback()

                json_response(

                    self,

                    {

                        "error": "Experience not found"

                    },

                    404

                )

                return

            if experience["spots"] < quantity:

                conn.rollback()

                json_response(

                    self,

                    {

                        "error": "Not enough spots available",

                        "available": experience["spots"]

                    },

                    409

                )

                return

            total = (

                float(experience["price"])

                * quantity

            )

            booking_code = make_booking_code()

            conn.execute("""

                INSERT INTO bookings

                (

                    booking_code,

                    experience_id,

                    traveler_name,

                    traveler_email,

                    language,

                    quantity,

                    total,

                    status

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            """, (

                booking_code,

                experience_id,

                traveler_name,

                traveler_email,

                language,

                quantity,

                total,

                "confirmed"

            ))

            conn.execute("""

                UPDATE experiences

                SET spots = spots - ?

                WHERE id = ?

            """, (

                quantity,

                experience_id

            ))

            conn.commit()

            remaining = experience["spots"] - quantity

            json_response(

                self,

                {

                    "success": True,

                    "booking_code": booking_code,

                    "experience": experience["title"],

                    "quantity": quantity,

                    "total": round(total, 2),

                    "remaining_spots": remaining,

                    "language": language

                },

                201

            )

        except Exception as exc:

            conn.rollback()

            json_response(

                self,

                {

                    "error": "Booking failed",

                    "details": str(exc)

                },

                500

            )

        finally:

            conn.close()

    # -----------------------------------------------------

    # STATIC FILES

    # -----------------------------------------------------

    def serve_static(self, path):

        if path == "/":

            path = "/index.html"

        requested = path.lstrip("/")

        # Keep requests inside the static directory.

        safe_path = os.path.normpath(requested)

        if safe_path.startswith(".."):

            json_response(

                self,

                {"error": "Invalid path"},

                400

            )

            return

        file_path = os.path.join(

            STATIC_DIR,

            safe_path

        )

        if not os.path.isfile(file_path):

            json_response(

                self,

                {"error": "Page not found"},

                404

            )

            return

        content_types = {

            ".html": "text/html; charset=utf-8",

            ".css": "text/css; charset=utf-8",

            ".js": "application/javascript; charset=utf-8",

            ".json": "application/json; charset=utf-8",

            ".png": "image/png",

            ".jpg": "image/jpeg",

            ".jpeg": "image/jpeg",

            ".svg": "image/svg+xml",

            ".ico": "image/x-icon"

        }

        extension = os.path.splitext(

            file_path

        )[1].lower()

        content_type = content_types.get(

            extension,

            "application/octet-stream"

        )

        try:

            with open(file_path, "rb") as file:

                body = file.read()

            self.send_response(200)

            self.send_header(

                "Content-Type",

                content_type

            )

            self.send_header(

                "Content-Length",

                str(len(body))

            )

            self.send_cors()

            self.end_headers()

            self.wfile.write(body)

        except Exception as exc:

            json_response(

                self,

                {

                    "error": "Unable to read file",

                    "details": str(exc)

                },

                500

            )

# ---------------------------------------------------------

# START APPLICATION

# ---------------------------------------------------------

if _name_ == "_main_":

    init_db()

    seed()

    print(

        f"Guam AI Host V4 running on "

        f"http://{HOST}:{PORT}"

    )

    server = ThreadingHTTPServer(

        (HOST, PORT),

        GuamAIHostHandler

    )

    server.serve_forever()
