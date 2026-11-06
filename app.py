import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path

import requests
import streamlit as st

GROQ_BASE = "https://api.groq.com/openai/v1"
FILLERS = {"um", "uh", "umm", "erm", "like", "basically", "actually", "literally"}

st.set_page_config(page_title="Interview Coach", page_icon="🎤")


def secret(name, default=None):
    """Read from Streamlit secrets, then environment variables."""
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, default)


LLM_MODEL = secret("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
STT_MODEL = secret("GROQ_STT_MODEL", "whisper-large-v3-turbo")


# ---------------- Groq (free tier) ----------------
class AIError(Exception):
    pass


def _headers():
    key = secret("GROQ_API_KEY")
    if not key:
        raise AIError("GROQ_API_KEY is missing. The admin needs to add it in Secrets.")
    return {"Authorization": f"Bearer {key}"}


def _check(r):
    if r.status_code == 429:
        raise AIError("The free AI quota is busy right now. Wait a minute and try again.")
    if r.status_code in (401, 403):
        raise AIError("The AI service rejected the API key. The admin should check GROQ_API_KEY.")
    if not r.ok:
        raise AIError(f"AI service error {r.status_code}: {r.text[:200]}")
    return r.json()


def ask_llm(prompt, json_mode=False, max_tokens=900):
    body = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = requests.post(f"{GROQ_BASE}/chat/completions", headers=_headers(), json=body, timeout=60)
    return _check(r)["choices"][0]["message"]["content"]


def transcribe(audio_bytes):
    r = requests.post(
        f"{GROQ_BASE}/audio/transcriptions",
        headers=_headers(),
        files={"file": ("answer.wav", audio_bytes, "audio/wav")},
        data={
            "model": STT_MODEL,
            "response_format": "verbose_json",
            "timestamp_granularities[]": "word",
            "language": "en",
            "temperature": "0",
        },
        timeout=120,
    )
    data = _check(r)
    return (data.get("text") or "").strip(), data.get("words") or []


# ---------------- Interview logic ----------------
def new_question(role, kind, level, asked):
    avoid = "; ".join(asked[-5:]) or "none"
    q = ask_llm(
        f"Ask ONE {kind} interview question for a {level} {role} candidate. "
        f"Do not repeat these earlier questions: {avoid}. "
        f"Reply with the question only, no extra text.",
        max_tokens=100,
    )
    return q.strip().strip('"')


def delivery_stats(words):
    if len(words) < 2:
        return {"wpm": 0, "filler_count": 0, "long_pauses": 0, "duration_sec": 0}
    tokens = [re.sub(r"[^\w']", "", str(w.get("word", "")).lower()) for w in words]
    duration = max(words[-1]["end"] - words[0]["start"], 0.1)
    pauses = [b["start"] - a["end"] for a, b in zip(words, words[1:]) if b["start"] - a["end"] > 1.0]
    return {
        "wpm": round(len(words) / duration * 60),
        "filler_count": sum(t in FILLERS for t in tokens),
        "long_pauses": len(pauses),
        "duration_sec": round(duration),
    }


def as_list(x):
    if isinstance(x, list):
        return [str(i) for i in x]
    return [str(x)] if x else []


def analyze(question, answer, stats, role, kind):
    raw = ask_llm(
        f"""You are a strict but kind interview coach for a {role} {kind} interview.
Question: {question}
Candidate's spoken answer (transcript): {answer}
Delivery stats: {stats}

Return ONLY a JSON object with exactly these keys:
"score": integer 1-10,
"strengths": list of short strings,
"missing": list of short strings (what the answer lacked),
"structure_feedback": string (for behavioral questions, check STAR),
"delivery_feedback": string (use the stats),
"improved_answer": string (a stronger version using the candidate's own content).""",
        json_mode=True,
        max_tokens=1200,
    )
    data = json.loads(raw)
    try:
        score = int(float(data.get("score", 0)))
    except (TypeError, ValueError):
        score = 0
    return {
        "score": max(0, min(score, 10)),
        "strengths": as_list(data.get("strengths")),
        "missing": as_list(data.get("missing")),
        "structure_feedback": str(data.get("structure_feedback", "")),
        "delivery_feedback": str(data.get("delivery_feedback", "")),
        "improved_answer": str(data.get("improved_answer", "")),
    }


# ---------------- Login ----------------
USERS_FILE = Path(__file__).with_name("users.json")
HASH_ITER = 200_000


def load_users():
    # Deployed: users live in the USERS_JSON secret. Local: users.json file.
    raw = secret("USERS_JSON")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    try:
        return json.loads(USERS_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def check_login(username, password):
    rec = load_users().get(username.strip().lower())
    salt = bytes.fromhex(rec["salt"]) if rec else b"\x00" * 16
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, HASH_ITER).hex()
    return bool(rec) and hmac.compare_digest(digest, rec["hash"])


if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.fails = 0

if st.session_state.user is None:
    st.title("🎤 Voice Interview Coach")
    st.subheader("Sign in")
    if st.session_state.fails >= 5:
        st.error("Too many failed attempts. Please contact the admin.")
        st.stop()
    with st.form("login"):
        u = st.text_input("User ID")
        p = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        if check_login(u, p):
            st.session_state.user = u.strip().lower()
            st.rerun()
        else:
            st.session_state.fails += 1
            time.sleep(1)
            st.error("Wrong ID or password.")
    st.stop()

# ---------------- Main app (signed in) ----------------
st.title("🎤 Voice Interview Coach")

with st.sidebar:
    st.write(f"Signed in as **{st.session_state.user}**")
    if st.button("Sign out"):
        st.session_state.clear()
        st.rerun()
    role = st.text_input("Role", "Unity Game Developer")
    kind = st.selectbox("Interview type", ["HR", "Behavioral", "Technical", "Mixed"])
    level = st.selectbox("Level", ["fresher", "junior", "mid-level", "senior"])

if "asked" not in st.session_state:
    st.session_state.asked = []
    st.session_state.question = None
    st.session_state.history = []


def make_question():
    try:
        q = new_question(role, kind, level, st.session_state.asked)
    except (AIError, requests.RequestException) as e:
        st.error(str(e))
        st.stop()
    st.session_state.question = q
    st.session_state.asked.append(q)


if st.button("New question") or st.session_state.question is None:
    with st.spinner("Thinking of a question..."):
        make_question()

st.subheader(st.session_state.question)

audio = st.audio_input("Record your answer")

if audio and st.button("Analyze my answer"):
    try:
        with st.spinner("Transcribing..."):
            text, words = transcribe(audio.getvalue())
        if not text:
            st.warning("Couldn't hear anything. Try recording again.")
            st.stop()
        stats = delivery_stats(words)
        with st.spinner("Analyzing..."):
            fb = analyze(st.session_state.question, text, stats, role, kind)
    except AIError as e:
        st.error(str(e))
        st.stop()
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        st.error(f"Something went wrong, please try again. ({type(e).__name__})")
        st.stop()

    st.session_state.history.append(fb["score"])

    st.markdown("### Your transcript")
    st.write(text)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Score", f"{fb['score']}/10")
    c2.metric("Words/min", stats["wpm"])
    c3.metric("Fillers", stats["filler_count"])
    c4.metric("Long pauses", stats["long_pauses"])

    st.markdown("### ✅ Strengths")
    for s in fb["strengths"]:
        st.write(f"- {s}")
    st.markdown("### ⚠️ What was missing")
    for m in fb["missing"]:
        st.write(f"- {m}")
    st.markdown("### Structure")
    st.write(fb["structure_feedback"])
    st.markdown("### Delivery")
    st.write(fb["delivery_feedback"])
    st.markdown("### 💡 Stronger version")
    st.info(fb["improved_answer"])

if st.session_state.history:
    st.sidebar.markdown("### Progress")
    st.sidebar.line_chart(st.session_state.history)
