"""Accounts, solo run records and leaderboards for rhythmhit.scottshrimp.com.

Standard library only (VPS3 runs Python 3.10). Caddy forwards /api/* here and
serves everything else as static files. Settings come from the environment:

  RH_DB                 SQLite path (default /var/lib/rhythmhit/rhythmhit.sqlite3)
  RH_SONGS              songs.json of the live release, read for song validation
  RH_PORT               loopback port (default 8095)
  RH_ORIGIN             origin allowed to POST, e.g. https://rhythmhit.scottshrimp.com
  RH_COOKIE_SECURE      "0" only for local http testing
  RH_TURNSTILE_SITEKEY  public Cloudflare Turnstile site key
  RH_TURNSTILE_SECRET   Turnstile secret key
  RH_TURNSTILE_HOSTNAME hostname Turnstile must report (empty skips the check)

Scores come from the player's browser, so they are checked for consistency
(score range, combo bound, minimum play time) but cannot be proven genuine.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = os.environ.get("RH_DB", "/var/lib/rhythmhit/rhythmhit.sqlite3")
SONGS_PATH = os.environ.get("RH_SONGS", "/srv/rhythmhit/current/browser/songs.json")
PORT = int(os.environ.get("RH_PORT", "8095"))
ORIGIN = os.environ.get("RH_ORIGIN", "https://rhythmhit.scottshrimp.com")
COOKIE_SECURE = os.environ.get("RH_COOKIE_SECURE", "1") != "0"
TURNSTILE_SITEKEY = os.environ.get("RH_TURNSTILE_SITEKEY", "")
TURNSTILE_SECRET = os.environ.get("RH_TURNSTILE_SECRET", "")
TURNSTILE_HOSTNAME = os.environ.get("RH_TURNSTILE_HOSTNAME", "")
TURNSTILE_URL = os.environ.get("RH_TURNSTILE_URL",
                               "https://challenges.cloudflare.com/turnstile/v0/siteverify")

COOKIE = "rh_session"
SESSION_DAYS = 30
MAX_BODY = 4096
USERNAME = re.compile(r"[A-Za-z0-9_-]{3,20}")
SONG_ID = re.compile(r"[a-z0-9-]{1,64}")
SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}
RUN_MAX_AGE = 6 * 3600
OPEN_RUNS_PER_USER = 20
BOARD_SIZE = 50

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    song_id TEXT NOT NULL,
    notes INTEGER NOT NULL,
    started_at INTEGER NOT NULL,
    finished_at INTEGER,
    score INTEGER,
    miss INTEGER,
    best_combo INTEGER
);
CREATE INDEX IF NOT EXISTS runs_board ON runs(song_id, score DESC) WHERE finished_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS runs_user ON runs(user_id, finished_at);
"""


class ApiError(Exception):
    def __init__(self, status, code):
        super().__init__(code)
        self.status = status
        self.code = code


def connect():
    db = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 10000")
    return db


def init_db():
    db = connect()
    db.execute("PRAGMA journal_mode = WAL")
    db.executescript(SCHEMA)
    db.close()


# ---------- Passwords and sessions ----------

def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, dklen=32, maxmem=64 * 1024 * 1024, **SCRYPT)
    return "scrypt$%d$%d$%d$%s$%s" % (SCRYPT["n"], SCRYPT["r"], SCRYPT["p"], salt.hex(), key.hex())


def check_password(password, stored):
    try:
        _, n, r, p, salt, key = stored.split("$")
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r),
                                p=int(p), dklen=32, maxmem=64 * 1024 * 1024)
    except ValueError:
        return False
    return hmac.compare_digest(actual.hex(), key)


# Unknown usernames still pay for one scrypt so timing does not reveal them.
DUMMY_HASH = hash_password(secrets.token_hex(8))


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


# ---------- Rate limits (per process, sliding window) ----------

class Limiter:
    def __init__(self):
        self.lock = threading.Lock()
        self.hits = defaultdict(deque)

    def allow(self, key, limit, window):
        now = time.monotonic()
        with self.lock:
            hits = self.hits[key]
            while hits and now - hits[0] > window:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            if len(self.hits) > 50000:
                self.hits = defaultdict(deque, {k: v for k, v in self.hits.items() if v})
            return True


limiter = Limiter()


# ---------- Songs ----------

_songs = {"mtime": None, "songs": {}}
_songs_lock = threading.Lock()


def songs():
    """Song id -> {title, duration, notes}, reloaded when a release changes it."""
    try:
        mtime = os.stat(SONGS_PATH).st_mtime_ns
    except OSError:
        return _songs["songs"]
    with _songs_lock:
        if mtime != _songs["mtime"]:
            with open(SONGS_PATH, encoding="utf-8") as handle:
                catalog = json.load(handle)
            _songs["songs"] = {
                song["id"]: {"title": song["title"], "duration": int(song["duration"]),
                             "notes": len(song["notes"])}
                for song in catalog if SONG_ID.fullmatch(str(song.get("id", "")))
            }
            _songs["mtime"] = mtime
        return _songs["songs"]


# ---------- Turnstile ----------

def verify_turnstile(token, ip):
    if not TURNSTILE_SECRET:
        raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "signup_unavailable")
    if not isinstance(token, str) or not 0 < len(token) <= 2048:
        raise ApiError(HTTPStatus.BAD_REQUEST, "captcha_failed")
    form = {"secret": TURNSTILE_SECRET, "response": token,
            "idempotency_key": secrets.token_hex(16)}
    if ip:
        form["remoteip"] = ip
    request = urllib.request.Request(TURNSTILE_URL, data=urllib.parse.urlencode(form).encode())
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            outcome = json.load(response)
    except (OSError, ValueError):
        raise ApiError(HTTPStatus.BAD_GATEWAY, "captcha_unreachable") from None
    if not outcome.get("success"):
        raise ApiError(HTTPStatus.BAD_REQUEST, "captcha_failed")
    if TURNSTILE_HOSTNAME and outcome.get("hostname") != TURNSTILE_HOSTNAME:
        raise ApiError(HTTPStatus.BAD_REQUEST, "captcha_failed")


# ---------- Run validation ----------

def plausible(notes, score, miss, best_combo):
    """Score rules from the firmware: PERFECT +100, GOOD +50, MISS 0."""
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in (score, miss, best_combo)):
        return False
    hits = notes - miss
    if not (0 <= miss <= notes and 50 * hits <= score <= 100 * hits and best_combo <= hits):
        return False
    # Misses split the hits into at most miss + 1 streaks.
    return best_combo * (miss + 1) >= hits


# ---------- HTTP ----------

class Handler(BaseHTTPRequestHandler):
    server_version = "rhythmhit-api"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # Caddy keeps access logs; skip IPs here.
        pass

    def client_ip(self):
        return self.headers.get("X-Real-IP", "").strip()[:64] or self.client_address[0]

    def send_json(self, status, payload, cookie=None):
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def session_cookie(self, token, max_age):
        parts = [f"{COOKIE}={token}", "Path=/api", "HttpOnly", "SameSite=Lax", f"Max-Age={max_age}"]
        if COOKIE_SECURE:
            parts.append("Secure")
        return "; ".join(parts)

    def cookie_token(self):
        for part in self.headers.get("Cookie", "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == COOKIE and re.fullmatch(r"[A-Za-z0-9_-]{20,100}", value):
                return value
        return None

    def current_user(self, db):
        token = self.cookie_token()
        if not token:
            return None
        return db.execute(
            "SELECT users.id, users.name FROM sessions JOIN users ON users.id = sessions.user_id "
            "WHERE token_hash = ? AND expires_at > ?", (token_hash(token), int(time.time()))).fetchone()

    def require_user(self, db):
        user = self.current_user(db)
        if user is None:
            raise ApiError(HTTPStatus.UNAUTHORIZED, "login_required")
        return user

    def read_json(self):
        if self.headers.get("Origin") != ORIGIN:
            raise ApiError(HTTPStatus.FORBIDDEN, "bad_origin")
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            raise ApiError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "json_required")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            raise ApiError(HTTPStatus.LENGTH_REQUIRED, "length_required") from None
        if not 0 <= length <= MAX_BODY:
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "too_large")
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            raise ApiError(HTTPStatus.BAD_REQUEST, "bad_json") from None
        if not isinstance(payload, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "bad_json")
        return payload

    def dispatch(self, method):
        path = urllib.parse.urlsplit(self.path)
        route = ROUTES.get((method, path.path))
        db = None
        try:
            if route is None:
                raise ApiError(HTTPStatus.NOT_FOUND, "not_found")
            payload = self.read_json() if method == "POST" else urllib.parse.parse_qs(path.query)
            db = connect()
            status, body, cookie = route(self, db, payload)
            self.send_json(status, body, cookie)
        except ApiError as error:
            if method == "POST":
                self.close_connection = True  # an unread body must not leak into the next request
            self.send_json(error.status, {"error": error.code})
        except Exception:  # noqa: BLE001 - never leak details to the client
            self.close_connection = True
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "server_error"})
            raise
        finally:
            if db is not None:
                db.close()

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")


def user_body(user):
    return {"name": user["name"]} if user else None


def get_health(handler, db, _):
    db.execute("SELECT 1").fetchone()
    return HTTPStatus.OK, {"ok": True, "songs": len(songs())}, None


def get_me(handler, db, _):
    user = handler.current_user(db)
    return HTTPStatus.OK, {"user": user_body(user), "turnstile_site_key": TURNSTILE_SITEKEY}, None


def start_session(handler, db, user_id):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
    db.execute("INSERT INTO sessions VALUES (?, ?, ?)",
               (token_hash(token), user_id, now + SESSION_DAYS * 86400))
    return handler.session_cookie(token, SESSION_DAYS * 86400)


def credentials(payload):
    name, password = payload.get("username"), payload.get("password")
    if not isinstance(name, str) or not USERNAME.fullmatch(name):
        raise ApiError(HTTPStatus.BAD_REQUEST, "bad_username")
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise ApiError(HTTPStatus.BAD_REQUEST, "bad_password")
    return name, password


def post_signup(handler, db, payload):
    ip = handler.client_ip()
    name, password = credentials(payload)
    if not limiter.allow(("signup", ip), 5, 3600):
        raise ApiError(HTTPStatus.TOO_MANY_REQUESTS, "rate_limited")
    if db.execute("SELECT 1 FROM users WHERE name = ?", (name,)).fetchone():
        raise ApiError(HTTPStatus.CONFLICT, "username_taken")
    verify_turnstile(payload.get("turnstile"), ip)
    stored = hash_password(password)
    try:
        cursor = db.execute("INSERT INTO users (name, password, created_at) VALUES (?, ?, ?)",
                            (name, stored, int(time.time())))
    except sqlite3.IntegrityError:
        raise ApiError(HTTPStatus.CONFLICT, "username_taken") from None
    cookie = start_session(handler, db, cursor.lastrowid)
    return HTTPStatus.CREATED, {"user": {"name": name}}, cookie


def post_login(handler, db, payload):
    ip = handler.client_ip()
    name, password = payload.get("username"), payload.get("password")
    if not isinstance(name, str) or not isinstance(password, str) or len(name) > 20 or len(password) > 128:
        raise ApiError(HTTPStatus.UNAUTHORIZED, "bad_credentials")
    if not (limiter.allow(("login", ip), 20, 900) and limiter.allow(("login-user", name.lower()), 10, 900)):
        raise ApiError(HTTPStatus.TOO_MANY_REQUESTS, "rate_limited")
    verify_turnstile(payload.get("turnstile"), ip)
    user = db.execute("SELECT id, name, password FROM users WHERE name = ?", (name,)).fetchone()
    if not check_password(password, user["password"] if user else DUMMY_HASH) or user is None:
        raise ApiError(HTTPStatus.UNAUTHORIZED, "bad_credentials")
    cookie = start_session(handler, db, user["id"])
    return HTTPStatus.OK, {"user": {"name": user["name"]}}, cookie


def post_logout(handler, db, _):
    token = handler.cookie_token()
    if token:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))
    return HTTPStatus.OK, {"user": None}, handler.session_cookie("", 0)


def post_run_start(handler, db, payload):
    user = handler.require_user(db)
    song_id = payload.get("song_id")
    song = songs().get(song_id) if isinstance(song_id, str) else None
    if song is None:
        raise ApiError(HTTPStatus.BAD_REQUEST, "unknown_song")
    now = int(time.time())
    db.execute("DELETE FROM runs WHERE finished_at IS NULL AND started_at < ?", (now - RUN_MAX_AGE,))
    open_runs = db.execute("SELECT COUNT(*) FROM runs WHERE user_id = ? AND finished_at IS NULL",
                           (user["id"],)).fetchone()[0]
    if open_runs >= OPEN_RUNS_PER_USER:
        db.execute("DELETE FROM runs WHERE id IN (SELECT id FROM runs WHERE user_id = ? AND finished_at IS NULL "
                   "ORDER BY started_at LIMIT ?)", (user["id"], open_runs - OPEN_RUNS_PER_USER + 1))
    run_id = secrets.token_urlsafe(16)
    db.execute("INSERT INTO runs (id, user_id, song_id, notes, started_at) VALUES (?, ?, ?, ?, ?)",
               (run_id, user["id"], song_id, song["notes"], now))
    return HTTPStatus.CREATED, {"run_id": run_id}, None


def post_run_finish(handler, db, payload):
    user = handler.require_user(db)
    run_id = payload.get("run_id")
    run = db.execute("SELECT * FROM runs WHERE id = ? AND user_id = ?",
                     (run_id if isinstance(run_id, str) else "", user["id"])).fetchone()
    if run is None or run["finished_at"] is not None:
        raise ApiError(HTTPStatus.NOT_FOUND, "unknown_run")
    song = songs().get(run["song_id"])
    now = int(time.time())
    # The run starts at song confirmation, so the full song must fit before it ends.
    if song is None or now - run["started_at"] < song["duration"] // 1000 - 1 or \
            now - run["started_at"] > RUN_MAX_AGE:
        raise ApiError(HTTPStatus.BAD_REQUEST, "run_rejected")
    score, miss, best = payload.get("score"), payload.get("miss"), payload.get("best_combo")
    if not plausible(run["notes"], score, miss, best):
        raise ApiError(HTTPStatus.BAD_REQUEST, "run_rejected")
    previous = db.execute("SELECT MAX(score) FROM runs WHERE user_id = ? AND song_id = ? "
                          "AND finished_at IS NOT NULL", (user["id"], run["song_id"])).fetchone()[0]
    db.execute("UPDATE runs SET finished_at = ?, score = ?, miss = ?, best_combo = ? WHERE id = ?",
               (now, score, miss, best, run["id"]))
    return HTTPStatus.OK, {
        "saved": True,
        "personal_best": previous is None or score > previous,
        "rank": rank_of(db, run["song_id"], user["id"]),
    }, None


BEST_PER_USER = """
SELECT * FROM (
    SELECT runs.user_id, users.name, runs.score, runs.miss, runs.best_combo, runs.finished_at,
           ROW_NUMBER() OVER (PARTITION BY runs.user_id ORDER BY runs.score DESC, runs.finished_at) AS pick
    FROM runs JOIN users ON users.id = runs.user_id
    WHERE runs.song_id = ? AND runs.finished_at IS NOT NULL
) WHERE pick = 1 ORDER BY score DESC, finished_at
"""


def rank_of(db, song_id, user_id):
    for index, row in enumerate(db.execute(BEST_PER_USER, (song_id,)), 1):
        if row["user_id"] == user_id:
            return index
    return None


def run_body(row, song):
    notes = song["notes"] if song else None
    return {
        "score": row["score"], "miss": row["miss"], "best_combo": row["best_combo"],
        "accuracy": round(row["score"] / (notes * 100) * 100, 1) if notes else None,
        "at": row["finished_at"],
    }


def get_leaderboard(handler, db, query):
    user = handler.require_user(db)
    catalog = songs()
    song_id = (query.get("song") or [next(iter(catalog), "")])[0]
    song = catalog.get(song_id)
    if song is None:
        raise ApiError(HTTPStatus.NOT_FOUND, "unknown_song")
    entries, me = [], None
    for index, row in enumerate(db.execute(BEST_PER_USER, (song_id,)), 1):
        entry = {"rank": index, "name": row["name"], "you": row["user_id"] == user["id"],
                 **run_body(row, song)}
        if index <= BOARD_SIZE:
            entries.append(entry)
        if entry["you"]:
            me = entry
    recent = [
        {"song_id": row["song_id"], "title": catalog.get(row["song_id"], {}).get("title", row["song_id"]),
         **run_body(row, catalog.get(row["song_id"]))}
        for row in db.execute("SELECT * FROM runs WHERE user_id = ? AND finished_at IS NOT NULL "
                              "ORDER BY finished_at DESC LIMIT 10", (user["id"],))
    ]
    return HTTPStatus.OK, {
        "user": user_body(user),
        "songs": [{"id": key, "title": value["title"], "notes": value["notes"]} for key, value in catalog.items()],
        "song": {"id": song_id, "title": song["title"], "notes": song["notes"]},
        "entries": entries,
        "me": me,
        "recent": recent,
    }, None


ROUTES = {
    ("GET", "/api/health"): get_health,
    ("GET", "/api/me"): get_me,
    ("GET", "/api/leaderboard"): get_leaderboard,
    ("POST", "/api/signup"): post_signup,
    ("POST", "/api/login"): post_login,
    ("POST", "/api/logout"): post_logout,
    ("POST", "/api/runs/start"): post_run_start,
    ("POST", "/api/runs/finish"): post_run_finish,
}


def main():
    init_db()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
