"""Real accounts: sign up / sign in / forgot-password with an emailed 6-digit code.
Users live in users.db (SQLite file next to the app). Passwords are stored as salted scrypt hashes."""
import hashlib
import hmac
import os
import re
import secrets
import smtplib
import sqlite3
import ssl
import time
from email.message import EmailMessage
from pathlib import Path

import streamlit as st

DB = Path(__file__).parent / "users.db"
CODE_TTL, MAX_CODE_TRIES = 600, 5          # code valid 10 min, 5 wrong tries
MAX_FAILS, LOCK_SECS = 5, 300              # 5 wrong passwords → locked 5 min
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(email TEXT PRIMARY KEY, name TEXT, pw_hash TEXT, salt TEXT, created_at REAL,
                                     fails INTEGER DEFAULT 0, locked_until REAL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS reset_codes(email TEXT PRIMARY KEY, code_hash TEXT, expires_at REAL, tries INTEGER DEFAULT 0);""")
    return con


def _hash(pw: str, salt: bytes) -> str:
    return hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32).hex()


def _norm(email: str) -> str:
    return (email or "").strip().lower()


def check_password_rules(pw: str):
    if len(pw) < 8:
        return "Password must be at least 8 characters."
    if not (re.search(r"[A-Za-z]", pw) and re.search(r"\d", pw)):
        return "Password must contain letters and numbers."
    return None


# ───────────── accounts ─────────────
def register(name: str, email: str, pw: str, pw2: str):
    email, name = _norm(email), (name or "").strip()
    if not name:
        return False, "Please enter your name."
    if not EMAIL_RE.match(email):
        return False, "Enter a valid email address."
    if pw != pw2:
        return False, "Passwords do not match."
    if (err := check_password_rules(pw)):
        return False, err
    with _db() as con:
        if con.execute("SELECT 1 FROM users WHERE email=?", [email]).fetchone():
            return False, "This email is already registered. Please sign in."
        salt = secrets.token_bytes(16)
        con.execute("INSERT INTO users(email,name,pw_hash,salt,created_at) VALUES (?,?,?,?,?)",
                    [email, name, _hash(pw, salt), salt.hex(), time.time()])
    return True, name


def authenticate(email: str, pw: str):
    """Returns (ok, message_or_name)."""
    email = _norm(email)
    with _db() as con:
        u = con.execute("SELECT * FROM users WHERE email=?", [email]).fetchone()
        if not u:
            _hash(pw, b"0" * 16)  # same cost as a real check
            return False, "Wrong email or password."
        if u["locked_until"] and u["locked_until"] > time.time():
            return False, f"Too many wrong attempts. Try again in {int((u['locked_until'] - time.time()) // 60) + 1} min."
        if hmac.compare_digest(_hash(pw, bytes.fromhex(u["salt"])), u["pw_hash"]):
            con.execute("UPDATE users SET fails=0, locked_until=0 WHERE email=?", [email])
            return True, u["name"]
        fails = u["fails"] + 1
        lock = time.time() + LOCK_SECS if fails >= MAX_FAILS else 0
        con.execute("UPDATE users SET fails=?, locked_until=? WHERE email=?", [0 if lock else fails, lock, email])
        return False, "Wrong email or password."


# ───────────── forgot password ─────────────
def create_reset_code(email: str):
    """Returns the plain 6-digit code if the account exists, else None (caller shows the same message either way)."""
    email = _norm(email)
    with _db() as con:
        if not con.execute("SELECT 1 FROM users WHERE email=?", [email]).fetchone():
            return None
        code = f"{secrets.randbelow(10 ** 6):06d}"
        con.execute("INSERT OR REPLACE INTO reset_codes(email,code_hash,expires_at,tries) VALUES (?,?,?,0)",
                    [email, hashlib.sha256(code.encode()).hexdigest(), time.time() + CODE_TTL])
    return code


def reset_password(email: str, code: str, pw: str, pw2: str):
    email = _norm(email)
    if pw != pw2:
        return False, "Passwords do not match."
    if (err := check_password_rules(pw)):
        return False, err
    with _db() as con:
        r = con.execute("SELECT * FROM reset_codes WHERE email=?", [email]).fetchone()
        if not r or r["expires_at"] < time.time():
            return False, "Code expired or not found. Request a new code."
        if r["tries"] >= MAX_CODE_TRIES:
            con.execute("DELETE FROM reset_codes WHERE email=?", [email])
            return False, "Too many wrong codes. Request a new code."
        if not hmac.compare_digest(hashlib.sha256((code or "").strip().encode()).hexdigest(), r["code_hash"]):
            con.execute("UPDATE reset_codes SET tries=tries+1 WHERE email=?", [email])
            return False, "Wrong code."
        salt = secrets.token_bytes(16)
        con.execute("UPDATE users SET pw_hash=?, salt=?, fails=0, locked_until=0 WHERE email=?", [_hash(pw, salt), salt.hex(), email])
        con.execute("DELETE FROM reset_codes WHERE email=?", [email])
    return True, "Password updated. You can sign in now."


# ───────────── email ─────────────
SECRETS = Path(__file__).parent / ".streamlit" / "secrets.toml"


def _secrets() -> dict:
    """st.secrets first; if that is empty, read <project>/.streamlit/secrets.toml directly (BOM-safe)."""
    try:
        d = {k: (dict(v) if hasattr(v, "keys") else v) for k, v in st.secrets.items()}
    except Exception:  # noqa: BLE001
        d = {}
    if not d:
        try:
            import tomllib
            d = tomllib.loads(SECRETS.read_text(encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            d = {}
    return d


def diagnose() -> str:
    """Plain-language reason why email / dev mode is not active (shown to the person setting the app up)."""
    if not SECRETS.exists():
        wrong = SECRETS.with_name("secrets.toml.txt")
        hint = " (found `secrets.toml.txt` — remove the `.txt`)" if wrong.exists() else ""
        return f"Settings file not found. Create `{SECRETS}`{hint}"
    d = _secrets()
    if not d:
        return f"`{SECRETS}` exists but could not be read — check for typos (strings need \" \"), then restart the app."
    if "smtp" not in d and "dev_show_code" not in d:
        return "secrets.toml has neither `[smtp]` nor `dev_show_code = true`."
    return "Settings found but incomplete — `[smtp]` needs host, user and password."


def _cfg() -> dict:
    d = _secrets()
    s = d.get("smtp") or {}
    dev = bool(d.get("dev_show_code", False))
    g = lambda k, env: s.get(k) or os.getenv(env)
    user = g("user", "SMTP_USER")
    return dict(host=g("host", "SMTP_HOST"), port=int(g("port", "SMTP_PORT") or 587), user=user,
                password=g("password", "SMTP_PASSWORD"), sender=g("sender", "SMTP_FROM") or user,
                dev=dev or os.getenv("DEV_SHOW_CODE") == "1")


def email_configured() -> bool:
    c = _cfg()
    return bool(c["host"] and c["user"] and c["password"])


def dev_mode() -> bool:
    return _cfg()["dev"]


def send_code_email(to: str, code: str):
    c = _cfg()
    if not (c["host"] and c["user"] and c["password"]):
        return False, "Email (SMTP) is not configured."
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = "Your CityCare password reset code", f"CityCare Analytics <{c['sender']}>", to
    msg.set_content(f"Your CityCare password reset code is:\n\n    {code}\n\nIt is valid for {CODE_TTL // 60} minutes. "
                    "If you did not request this, you can ignore this email.")
    try:
        if c["port"] == 465:
            with smtplib.SMTP_SSL(c["host"], 465, context=ssl.create_default_context(), timeout=20) as s:
                s.login(c["user"], c["password"]); s.send_message(msg)
        else:
            with smtplib.SMTP(c["host"], c["port"], timeout=20) as s:
                s.starttls(context=ssl.create_default_context()); s.login(c["user"], c["password"]); s.send_message(msg)
    except Exception as e:  # noqa: BLE001
        return False, f"Could not send email ({type(e).__name__}). Check SMTP settings."
    return True, ""