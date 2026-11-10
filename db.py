"""Database and password helpers for ARticulate. Talks to Supabase through its REST API."""
import hashlib
import hmac
import os
import secrets as pysecrets
from datetime import datetime, timedelta, timezone

import requests
import streamlit as st

HASH_ITER = 200_000
PW_ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
IST = timezone(timedelta(hours=5, minutes=30))


def secret(name, default=None):
    """Read from Streamlit secrets, then from environment variables."""
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, default)


# ---------------- passwords ----------------
def hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    return salt.hex(), hashlib.pbkdf2_hmac("sha256", password.encode(), salt, HASH_ITER).hex()


def verify_password(password, salt_hex, hash_hex):
    try:
        salt = bytes.fromhex(salt_hex)
    except (ValueError, TypeError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, HASH_ITER).hex()
    return hmac.compare_digest(digest, str(hash_hex))


def new_password(length=8):
    return "".join(pysecrets.choice(PW_ALPHABET) for _ in range(length))


# ---------------- REST plumbing ----------------
class DBError(Exception):
    pass


class DBConflict(DBError):
    pass


def _clean(value):
    return str(value or "").strip().strip("\"'").strip()


def base_url():
    """Tidy up SUPABASE_URL so small copy-paste slips still work."""
    url = _clean(secret("SUPABASE_URL")).rstrip("/")
    for suffix in ("/rest/v1", "/rest"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + (url if "." in url else f"{url}.supabase.co")
    return url


def db_configured():
    return bool(base_url() and _clean(secret("SUPABASE_SECRET_KEY")))


def db(method, table, params=None, body=None, prefer=None):
    url, key = base_url(), _clean(secret("SUPABASE_SECRET_KEY"))
    if not (url and key):
        raise DBError("The database is not connected yet.")
    headers = {"apikey": key, "Content-Type": "application/json"}
    if key.startswith("eyJ"):  # old-style JWT keys also go in the Authorization header; sb_secret_ keys must not
        headers["Authorization"] = f"Bearer {key}"
    if prefer:
        headers["Prefer"] = prefer
    try:
        r = requests.request(method, f"{url}/rest/v1/{table}", headers=headers,
                             params=params, json=body, timeout=20)
    except (requests.exceptions.MissingSchema, requests.exceptions.InvalidSchema, requests.exceptions.InvalidURL):
        raise DBError("SUPABASE_URL looks wrong. It should look like https://abcdefgh.supabase.co")
    except requests.exceptions.ConnectionError:
        raise DBError("Can't reach the database. Check that SUPABASE_URL is spelled exactly as in Supabase "
                      "(https://<project>.supabase.co) and that the project is not paused.")
    except requests.RequestException:
        raise DBError("The database did not answer in time. Please try again.")
    if r.status_code in (401, 403):
        raise DBError("The database rejected the key. Check SUPABASE_SECRET_KEY in Secrets.")
    if r.status_code == 409:
        raise DBConflict("That record already exists.")
    if r.status_code == 404 and ("PGRST205" in r.text or "schema cache" in r.text or "PGRST125" in r.text):
        raise DBError("The database tables don't exist yet. Run supabase_setup.sql in the Supabase SQL Editor.")
    if not r.ok:
        raise DBError(f"Database error {r.status_code}: {r.text[:200]}")
    return r.json() if r.text else []


def db_all(table, params, cap=30000, page=1000):
    """Read many rows (the API returns at most 1000 per request)."""
    out, offset = [], 0
    while len(out) < cap:
        rows = db("GET", table, {**params, "limit": str(page), "offset": str(offset)})
        out += rows
        if len(rows) < page:
            break
        offset += page
    return out


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------------- users ----------------
def get_user(username):
    rows = db("GET", "users", {"select": "*", "username": f"eq.{username}", "limit": "1"})
    return rows[0] if rows else None


def create_user(username, name, password):
    salt, h = hash_password(password)
    db("POST", "users", body={"username": username, "name": name, "salt": salt, "hash": h, "role": "student"},
       prefer="return=minimal")


def existing_usernames():
    return {r["username"] for r in db_all("users", {"select": "username"})}


def create_users_bulk(rows):
    for i in range(0, len(rows), 200):
        db("POST", "users", body=rows[i:i + 200], prefer="return=minimal")


def list_students():
    return db_all("users", {"select": "username,name,active,created_at,last_login", "order": "username.asc"})


def set_password(username, password):
    salt, h = hash_password(password)
    db("PATCH", "users", {"username": f"eq.{username}"}, {"salt": salt, "hash": h}, prefer="return=minimal")


def set_active(username, active):
    db("PATCH", "users", {"username": f"eq.{username}"}, {"active": bool(active)}, prefer="return=minimal")


def delete_student(username):
    for table in ("attempts", "progress", "users"):
        db("DELETE", table, {"username": f"eq.{username}"}, prefer="return=minimal")


def touch_login(username):
    try:
        db("PATCH", "users", {"username": f"eq.{username}"}, {"last_login": now_iso()}, prefer="return=minimal")
    except DBError:
        pass


# ---------------- progress and attempts ----------------
def load_progress(username):
    rows = db("GET", "progress", {"select": "*", "username": f"eq.{username}", "limit": "1"})
    return rows[0] if rows else None


def save_progress(username, xp, streak, best_streak, badges):
    db("POST", "progress", {"on_conflict": "username"},
       {"username": username, "xp": xp, "streak": streak, "best_streak": best_streak,
        "badges": list(badges), "updated_at": now_iso()},
       prefer="resolution=merge-duplicates,return=minimal")


def add_attempt(**row):
    db("POST", "attempts", body=row, prefer="return=minimal")


def recent_scores(username, n=30):
    rows = db("GET", "attempts", {"select": "score", "username": f"eq.{username}",
                                  "order": "created_at.desc", "limit": str(n)})
    return [int(r["score"]) for r in reversed(rows)]


def count_today(username):
    since = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat()
    rows = db("GET", "attempts", {"select": "id", "username": f"eq.{username}",
                                  "created_at": f"gte.{since}", "limit": "1000"})
    return len(rows)


def student_attempts(username, limit=50):
    return db("GET", "attempts", {"select": "*", "username": f"eq.{username}",
                                  "order": "created_at.desc", "limit": str(limit)})


def attempts_overview():
    return db_all("attempts", {"select": "username,score,xp,created_at", "order": "created_at.desc"})


def all_progress():
    return db_all("progress", {"select": "username,xp,streak,best_streak"})


# ---------------- question bank ----------------
@st.cache_data(ttl=60, show_spinner=False)
def list_questions_cached():
    return db_all("questions", {"select": "id,text,category,key_points", "active": "eq.true", "order": "id.asc"}, cap=5000)


def list_questions():
    return db_all("questions", {"select": "id,text,category,key_points,active", "order": "id.asc"}, cap=10000)


def add_questions(rows, created_by=""):
    payload = [{**r, "created_by": created_by} for r in rows]
    for i in range(0, len(payload), 300):
        db("POST", "questions", body=payload[i:i + 300], prefer="return=minimal")
    list_questions_cached.clear()


def delete_questions(ids):
    for i in range(0, len(ids), 100):
        chunk = ",".join(str(int(x)) for x in ids[i:i + 100])
        db("DELETE", "questions", {"id": f"in.({chunk})"}, prefer="return=minimal")
    list_questions_cached.clear()


def clear_questions():
    db("DELETE", "questions", {"id": "gt.0"}, prefer="return=minimal")
    list_questions_cached.clear()
