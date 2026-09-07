if _name_ == "_main_": import os

    seed()

    host = "0.0.0.0"

    port = int(os.environ.get("PORT", "8000"))

    print(f"Guam AI Host V4 running on {host}:{port}")

    ThreadingHTTPServer((host, port), Handler).serve_forever()
import os

import json

import sqlite3

import uuid

from datetime import datetime

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pathlib import Path

from urllib.parse import urlparse

BASE = Path(_file_).resolve().parent

DB = BASE / "guam_host_v4.db"

STATIC = BASE / "static"

HOST = "0.0.0.0"

PORT = int(os.environ.get("PORT", "8000"))

# ============================================================

# DATABASE

# ============================================================

SCHEMA = """

CREATE TABLE IF NOT EXISTS experiences (

    id TEXT PRIMARY KEY,

    business TEXT NOT NULL,

    title TEXT NOT NULL,

    category TEXT NOT NULL,

    description TEXT NOT NULL,

    price REAL NOT NULL,

    starts_at TEXT NOT NULL,

    duration_min INTEGER NOT NULL,

    spots INTEGER NOT NULL,

    location TEXT NOT NULL,

    tags TEXT NOT NULL,

    active INTEGER NOT NULL DEFAULT 1,

    created_at TEXT NOT NULL

);

CREATE TABLE IF NOT EXISTS travelers (

    id TEXT PRIMARY KEY,

    name TEXT NOT NULL,

    email TEXT NOT NULL,

    language TEXT NOT NULL,

    budget REAL,

    interests TEXT,

    created_at TEXT NOT NULL

);

CREATE TABLE IF NOT EXISTS bookings (

    id TEXT PRIMARY KEY,

    confirmation TEXT UNIQUE NOT NULL,

    experience_id TEXT NOT NULL,

    traveler_id TEXT NOT NULL,

    qty INTEGER NOT NULL,

    total REAL NOT NULL,

    status TEXT NOT NULL,

    created_at TEXT NOT NULL

);

"""

# ============================================================

# SEED DATA

# ============================================================

SEED = [

    (

        "Sunset Beach Escape",

        "Tumon Sunset Tours",

        "beach",

        "Private sunset beach experience with a local host.",

        59,

        "2026-09-07 16:15",

        90,

        8,

        "Tumon",

        "romantic,beach,sunset,photo",

    ),

    (

        "Guam Food & Shopping Night",

        "Island Food Co.",

        "food",

        "Local food tasting followed by a curated shopping stop.",

        42,

        "2026-09-07 18:00",

        120,

        12,

        "Tumon",

        "food,shopping,local,korean,japanese",

    ),

    (

        "Ocean Adventure",

        "Guam Ocean Club",

        "ocean",

        "Guided ocean adventure with reef viewing and water time.",

        75,

        "2026-09-07 13:30",

        150,

        6,

        "Hagåtña",

        "ocean,adventure,family",

    ),

    (

        "Island Reset Spa",

        "Island Reset Spa",

        "wellness",

        "Relaxing island spa session designed for travelers.",

        69,

        "2026-09-07 15:30",

        90,

        3,

        "Tumon",

        "wellness,spa,relax,romantic",

    ),

    (

        "Guam Couple Photo Walk",

        "Guam Photo Co.",

        "photo",

        "Local photographer captures a couple around scenic Guam spots.",

        99,

        "2026-09-07 17:00",

        75,

        2,

        "Two Lovers Point",

        "photo,romantic,couple,sunset",

    ),

    (

        "Secret Beach Picnic",

        "Local Guam Experiences",

        "beach",

        "Small-group picnic at a quiet coastal location.",

        79,

        "2026-09-07 11:00",

        120,

        4,

        "West Guam",

        "beach,picnic,romantic,quiet",

    ),

]

# ============================================================

# DATABASE HELPERS

# ============================================================

def get_db():

    connection = sqlite3.connect(DB)

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    connection.executescript(SCHEMA)

    return connection

def seed_database():

    connection = get_db()

    count = connection.execute(

        "SELECT COUNT(*) FROM experiences"

    ).fetchone()[0]

    if count == 0:

        now = datetime.utcnow().isoformat()

        for (

            title,

            business,

            category,

            description,

            price,

            starts_at,

            duration_min,

            spots,

            location,

            tags,

        ) in SEED:

            connection.execute(

                """

                INSERT INTO experiences (

                    id,

                    business,

                    title,

                    category,

                    description,

                    price,

                    starts_at,

                    duration_min,

                    spots,

                    location,

                    tags,

                    created_at

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                """,

                (

                    str(uuid.uuid4()),

                    business,

                    title,

                    category,

                    description,

                    price,

                    starts_at,

                    duration_min,

                    spots,

                    location,

                    tags,

                    now,

                ),

            )

        connection.commit()

    connection.close()

def fetch_rows(sql, parameters=()):

    connection = get_db()

    results = [

        dict(row)

        for row in connection.execute(sql, parameters).fetchall()

    ]

    connection.close()

    return results

# ============================================================

# AI-STYLE RECOMMENDATION ENGINE

# ============================================================

def score_experience(experience, user_message, budget=None):

    searchable_text = " ".join(

        [

            experience["title"],

            experience["description"],

            experience["category"],

            experience["location"],

            experience["tags"],

        ]

    ).lower()

    words = [

        word.strip(".,!?;:")

        for word in user_message.lower().split()

        if len(word) > 2

    ]

    score = 0

    # Direct keyword matching

    for word in words:

        if word in searchable_text:

            score += 2

    # Intent groups

    intent_groups = {

        "romantic": [

            "romantic",

            "couple",

            "date",

            "sunset",

            "photo",

            "quiet",

        ],

        "family": [

            "family",

            "kid",

            "kids",

            "children",

        ],

        "food": [

            "food",

            "eat",

            "eating",

            "dinner",

            "lunch",

            "restaurant",

            "shopping",

        ],

        "adventure": [

            "adventure",

            "ocean",

            "active",

            "water",

            "reef",

        ],

        "relax": [

            "spa",

            "relax",

            "wellness",

            "massage",

        ],

        "beach": [

            "beach",

            "ocean",

            "sunset",

            "coast",

        ],

    }

    message = user_message.lower()

    for intent, keywords in intent_groups.items():

        if intent in message:

            for keyword in keywords:

                if keyword in searchable_text:

                    score += 2

    # Budget scoring

    if budget is not None:

        if experience["price"] <= budget:

            score += 5

        elif experience["price"] <= budget * 1.25:

            score += 1

        else:

            score -= 5

    # Inventory bonus

    if experience["spots"] > 0:

        score += 1

    return score

def generate_recommendations(message, budget=None):

    experiences = fetch_rows(

        """

        SELECT *

        FROM experiences

        WHERE active = 1

        AND spots > 0

        """

    )

    ranked = sorted(

        experiences,

        key=lambda experience: score_experience(

            experience,

            message,

            budget,

        ),

        reverse=True,

    )

    # Keep recommendations reasonably close to budget

    if budget is not None:

        filtered = [

            experience

            for experience in ranked

            if experience["price"] <= budget * 1.25

        ]

        if filtered:

            ranked = filtered

    return ranked[:4]

# ============================================================

# HTTP HANDLER

# ============================================================

class GuamAIHostHandler(BaseHTTPRequestHandler):

    server_version = "GuamAIHost/4.0"

    # --------------------------------------------------------

    # JSON RESPONSE

    # --------------------------------------------------------

    def send_json(self, data, status=200):

        response = json.dumps(

            data,

            ensure_ascii=False,

        ).encode("utf-8")

        self.send_response(status)

        self.send_header(

            "Content-Type",

            "application/json; charset=utf-8",

        )

        self.send_header(

            "Content-Length",

            str(len(response)),

        )

        self.send_header(

            "Access-Control-Allow-Origin",

            "*",

        )

        self.end_headers()

        self.wfile.write(response)

    # --------------------------------------------------------

    # REQUEST BODY

    # --------------------------------------------------------

    def get_json_body(self):

        length = int(

            self.headers.get(

                "Content-Length",

                "0",

            )

        )

        raw = self.rfile.read(length)

        if not raw:

            return {}

        return json.loads(raw.decode("utf-8"))

    # --------------------------------------------------------

    # GET

    # --------------------------------------------------------

    def do_GET(self):

        path = urlparse(self.path).path

        # Health check

        if path == "/api/health":

            self.send_json(

                {

                    "ok": True,

                    "service": "Guam AI Host",

                    "version": "4.0",

                    "time": datetime.utcnow().isoformat(),

                }

            )

            return

        # Experiences

        if path == "/api/experiences":

            experiences = fetch_rows(

                """

                SELECT *

                FROM experiences

                WHERE active = 1

                ORDER BY starts_at

                """

            )

            self.send_json(experiences)

            return

        # Businesses

        if path == "/api/businesses":

            businesses = fetch_rows(

                """

                SELECT

                    business,

                    COUNT(*) AS experience_count

                FROM experiences

                WHERE active = 1

                GROUP BY business

                ORDER BY business

                """

            )

            self.send_json(businesses)

            return

        # Bookings

        if path == "/api/bookings":

            bookings = fetch_rows(

                """

                SELECT

                    b.*,

                    e.title,

                    e.business,

                    t.name,

                    t.email,

                    t.language

                FROM bookings b

                JOIN experiences e

                    ON e.id = b.experience_id

                JOIN travelers t

                    ON t.id = b.traveler_id

                ORDER BY b.created_at DESC

                """

            )

            self.send_json(bookings)

            return

        # Dashboard statistics

        if path == "/api/stats":

            connection = get_db()

            travelers = connection.execute(

                "SELECT COUNT(*) FROM travelers"

            ).fetchone()[0]

            bookings = connection.execute(

                "SELECT COUNT(*) FROM bookings"

            ).fetchone()[0]

            gmv = connection.execute(

                """

                SELECT COALESCE(SUM(total), 0)

                FROM bookings

                WHERE status = 'confirmed'

                """

            ).fetchone()[0]

            live_offers = connection.execute(

                """

                SELECT COUNT(*)

                FROM experiences

                WHERE active = 1

                AND spots > 0

                """

            ).fetchone()[0]

            businesses = connection.execute(

                """

                SELECT COUNT(DISTINCT business)

                FROM experiences

                """

            ).fetchone()[0]

            connection.close()

            stats = {

                "travelers": travelers,

                "bookings": bookings,

                "gmv": round(float(gmv), 2),

                "live_offers": live_offers,

                "businesses": businesses,

                "estimated_commission": round(

                    float(gmv) * 0.15,

                    2,

                ),

            }

            self.send_json(stats)

            return

        # Static files

        self.serve_static(path)

    # --------------------------------------------------------

    # POST

    # --------------------------------------------------------

    def do_POST(self):

        path = urlparse(self.path).path

        try:

            body = self.get_json_body()

        except Exception:

            self.send_json(

                {

                    "error": "Invalid JSON request"

                },

                400,

            )

            return

        # ----------------------------------------------------

        # AI RECOMMENDATION

        # ----------------------------------------------------

        if path == "/api/recommend":

            message = str(

                body.get(

                    "message",

                    "",

                )

            ).strip()

            if not message:

                self.send_json(

                    {

                        "error": "Please describe what you want to do."

                    },

                    400,

                )

                return

            budget = body.get("budget")

            try:

                if budget not in (None, ""):

                    budget = float(budget)

                else:

                    budget = None

            except (ValueError, TypeError):

                budget = None

            recommendations = generate_recommendations(

                message,

                budget,

            )

            answer = (

                "I found a few Guam experiences that match "

                "what you're looking for."

            )

            lowered = message.lower()

            if "rain" in lowered or "weather" in lowered:

                answer += (

                    " Because weather can change quickly, "

                    "I'd keep a flexible backup activity."

                )

            if budget is not None:

                answer += (

                    f" I prioritized options around your "

                    f"${budget:.0f} budget."

                )

            self.send_json(

                {

                    "answer": answer,

                    "recommendations": recommendations,

                }

            )

            return

        # ----------------------------------------------------

        # CREATE EXPERIENCE

        # ----------------------------------------------------

        if path == "/api/experiences":

            required = [

                "business",

                "title",

                "category",

                "description",

                "price",

                "starts_at",

                "duration_min",

                "spots",

                "location",

            ]

            missing = [

                field

                for field in required

                if field not in body

            ]

            if missing:

                self.send_json(

                    {

                        "error": "Missing fields",

                        "fields": missing,

                    },

                    400,

                )

                return

            try:

                price = float(body["price"])

                duration = int(body["duration_min"])

                spots = int(body["spots"])

                if price < 0 or duration <= 0 or spots < 0:

                    raise ValueError

            except (ValueError, TypeError):

                self.send_json(

                    {

                        "error": "Invalid price, duration or spots."

                    },

                    400,

                )

                return

            experience_id = str(uuid.uuid4())

            connection = get_db()

            connection.execute(

                """

                INSERT INTO experiences (

                    id,

                    business,

                    title,

                    category,

                    description,

                    price,

                    starts_at,

                    duration_min,

                    spots,

                    location,

                    tags,

                    created_at

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                """,

                (

                    experience_id,

                    str(body["business"]).strip(),

                    str(body["title"]).strip(),

                    str(body["category"]).strip(),

                    str(body["description"]).strip(),

                    price,

                    str(body["starts_at"]).strip(),

                    duration,

                    spots,

                    str(body["location"]).strip(),

                    str(body.get("tags", "")).strip(),

                    datetime.utcnow().isoformat(),

                ),

            )

            connection.commit()

            connection.close()

            self.send_json(

                {

                    "ok": True,

                    "id": experience_id,

                    "message": "Experience published.",

                },

                201,

            )

            return

        # ----------------------------------------------------

        # BOOKING

        # ----------------------------------------------------

        if path == "/api/bookings":

            experience_id = body.get(

                "experience_id"

            )

            name = str(

                body.get(

                    "name",

                    "",

                )

            ).strip()

            email = str(

                body.get(

                    "email",

                    "",

                )

            ).strip()

            language = str(

                body.get(

                    "language",

                    "en",

                )

            )

            try:

                quantity = int(

                    body.get(

                        "qty",

                        1,

                    )

                )

            except (ValueError, TypeError):

                self.send_json(

                    {

                        "error": "Invalid quantity."

                    },

                    400,

                )

                return

            if (

                not experience_id

                or not name

                or "@" not in email

                or quantity < 1

            ):

                self.send_json(

                    {

                        "error": (

                            "Name, valid email, "

                            "experience and quantity "

                            "are required."

                        )

                    },

                    400,

                )

                return

            connection = get_db()

            # Begin transaction so inventory isn't

            # accidentally oversold in this prototype.

            connection.execute("BEGIN IMMEDIATE")

            experience = connection.execute(

                """

                SELECT *

                FROM experiences

                WHERE id = ?

                AND active = 1

                """,

                (experience_id,),

            ).fetchone()

            if not experience:

                connection.rollback()

                connection.close()

                self.send_json(

                    {

                        "error": "Experience unavailable."

                    },

                    404,

                )

                return

            if experience["spots"] < quantity:

                connection.rollback()

                connection.close()

                self.send_json(

                    {

                        "error": "Not enough spots available."

                    },

                    409,

                )

                return

            traveler_id = str(uuid.uuid4())

            booking_id = str(uuid.uuid4())

            confirmation = (

                "GAH-"

                + uuid.uuid4().hex[:8].upper()

            )

            total = round(

                float(experience["price"])

                * quantity,

                2,

            )

            connection.execute(

                """

                INSERT INTO travelers (

                    id,

                    name,

                    email,

                    language,

                    budget,

                    interests,

                    created_at

                )

                VALUES (?, ?, ?, ?, ?, ?, ?)

                """,

                (

                    traveler_id,

                    name,

                    email,

                    language,

                    body.get("budget"),

                    body.get("interests", ""),

                    datetime.utcnow().isoformat(),

                ),

            )

            connection.execute(

                """

                UPDATE experiences

                SET spots = spots - ?

                WHERE id = ?

                """,

                (

                    quantity,

                    experience_id,

                ),

            )

            connection.execute(

                """

                INSERT INTO bookings (

                    id,

                    confirmation,

                    experience_id,

                    traveler_id,

                    qty,

                    total,

                    status,

                    created_at

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?)

                """,

                (

                    booking_id,

                    confirmation,

                    experience_id,

                    traveler_id,

                    quantity,

                    total,

                    "confirmed",

                    datetime.utcnow().isoformat(),

                ),

            )

            connection.commit()

            connection.close()

            self.send_json(

                {

                    "ok": True,

                    "confirmation": confirmation,

                    "total": total,

                    "currency": "USD",

                    "message": "Booking confirmed.",

                },

                201,

            )

            return

        self.send_json(

            {

                "error": "Endpoint not found."

            },

            404,

        )

    # --------------------------------------------------------

    # STATIC FILE SERVER

    # --------------------------------------------------------

    def serve_static(self, path):

        if path == "/":

            relative = "index.html"

        else:

            relative = path.lstrip("/")

        requested = (

            STATIC / relative

        ).resolve()

        static_root = STATIC.resolve()

        # Prevent path traversal

        try:

            requested.relative_to(static_root)

        except ValueError:

            self.send_json(

                {

                    "error": "Forbidden"

                },

                403,

            )

            return

        if not requested.exists() or not requested.is_file():

            self.send_json(

                {

                    "error": "Page not found"

                },

                404,

            )

            return

        content = requested.read_bytes()

        content_types = {

            ".html": "text/html; charset=utf-8",

            ".css": "text/css; charset=utf-8",

            ".js": "application/javascript; charset=utf-8",

            ".json": "application/json; charset=utf-8",

            ".svg": "image/svg+xml",

            ".png": "image/png",

            ".jpg": "image/jpeg",

            ".jpeg": "image/jpeg",

            ".webp": "image/webp",

        }

        content_type = content_types.get(

            requested.suffix.lower(),

            "application/octet-stream",

        )

        self.send_response(200)

        self.send_header(

            "Content-Type",

            content_type,

        )

        self.send_header(

            "Content-Length",

            str(len(content)),

        )

        self.end_headers()

        self.wfile.write(content)

    # --------------------------------------------------------

    # OPTIONS / CORS

    # --------------------------------------------------------

    def do_OPTIONS(self):

        self.send_response(204)

        self.send_header(

            "Access-Control-Allow-Origin",

            "*",

        )

        self.send_header(

            "Access-Control-Allow-Methods",

            "GET, POST, OPTIONS",

        )

        self.send_header(

            "Access-Control-Allow-Headers",

            "Content-Type",

        )

        self.end_headers()

    # --------------------------------------------------------

    # LOGGING

    # --------------------------------------------------------

    def log_message(self, format, *args):

        print(

            "%s - %s"

            % (

                self.address_string(),

                format % args,

            )

        )

# ============================================================

# START SERVER

# ============================================================

if _name_ == "_main_":

    seed_database()

    print(

        "=================================================="

    )

    print(

        "🌴 Guam AI Host V4"

    )

    print(

        f"Server: http://{HOST}:{PORT}"

    )

    print(

        f"Database: {DB}"

    )

    print(

        "=================================================="

    )

    server = ThreadingHTTPServer(

        (HOST, PORT),

        GuamAIHostHandler,

    )

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print(

            "\nServer stopped."

        )

    finally:

        server.server_close()
