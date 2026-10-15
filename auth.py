import os
import json
import hmac
import hashlib
import base64
import sqlite3
import secrets
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./linkbolt.db").replace("sqlite:///", "") or "linkbolt.db"
SECRET = os.getenv("JWT_SECRET", "change-me-linkbolt")


def b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()


def check_pw(password: str, salt: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_pw(password, salt), hashed)


def make_token(email: str) -> str:
    h = b64e(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    p = b64e(json.dumps({
        "sub": email,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()),
    }).encode())
    s = b64e(hmac.new(SECRET.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{s}"


def read_token(token: str):
    try:
        h, p, s = token.split(".")
        exp = b64e(hmac.new(SECRET.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(exp, s):
            return None
        data = json.loads(b64d(p))
        if data.get("exp", 0) < int(datetime.now(timezone.utc).timestamp()):
            return None
        return data
    except Exception:
        return None


def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def now():
    return datetime.now(timezone.utc).isoformat()


def new_code(n: int = 6) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(n))


def init():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, pw TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS links(
        code TEXT PRIMARY KEY, url TEXT, owner TEXT,
        clicks INTEGER DEFAULT 0, created TEXT)""")
    if c.execute("SELECT COUNT(*) c FROM links").fetchone()["c"] == 0:
        for code, url in [("ytlink", "https://youtube.com/"),
                          ("goog01", "https://google.com/")]:
            c.execute("INSERT OR IGNORE INTO links VALUES(?,?,?,?,?)",
                      (code, url, "admin@linkbolt.test", 3, now()))
        c.commit()
    if c.execute("SELECT COUNT(*) c FROM users WHERE email='admin@linkbolt.test'").fetchone()["c"] == 0:
        c.execute("INSERT INTO users(name,email,pw) VALUES(?,?,?)",
                  ("Demo", "admin@linkbolt.test",
                   hash_pw("admin123", "admin@linkbolt.test")))
        c.commit()
