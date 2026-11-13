import html
import json
import random
import re
import time

import requests
import streamlit as st
import streamlit.components.v1 as components

import art
from admin import render_admin
from db import (DBError, add_attempt, count_today, db_configured, get_user, list_questions_cached,
                load_progress, recent_scores, save_progress, secret, touch_login, verify_password)

GROQ_BASE = "https://api.groq.com/openai/v1"
FILLERS = {"um", "uh", "umm", "erm", "like", "basically", "actually", "literally"}

st.set_page_config(page_title="ARticulate", page_icon="🥽")


APP_NAME = "ARticulate"
TAGLINE = "Step into your interview. Answer out loud, earn XP, level up."
st.markdown(art.build_css() + art.particles_html(), unsafe_allow_html=True)

DAILY_LIMIT = int(secret("DAILY_LIMIT", 10))  # answers per student per day (protects the free AI quota)
LLM_MODEL = secret("GROQ_LLM_MODEL", "openai/gpt-oss-20b")
# Groq changes its model list often; if the main model is gone we try these in order.
FALLBACK_MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.1-8b-instant"]
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


def _post(url, **kw):
    """POST to Groq, waiting a few seconds and retrying when the free quota says 'slow down'."""
    for attempt in range(3):
        r = requests.post(url, **kw)
        if r.status_code == 429 and attempt < 2:
            try:
                wait = float(r.headers.get("retry-after", 4))
            except (ValueError, AttributeError):
                wait = 4
            time.sleep(min(wait, 8))
            continue
        return r
    return r


def _chat(model, prompt, json_mode, max_tokens):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }
    if "gpt-oss" in model:
        # reasoning models spend tokens on thinking, so keep it short and leave headroom
        body["reasoning_effort"] = "low"
        body["max_completion_tokens"] = max_tokens + 600
    else:
        body["max_completion_tokens"] = max_tokens
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    return _post(f"{GROQ_BASE}/chat/completions", headers=_headers(), json=body, timeout=90)


def ask_llm(prompt, json_mode=False, max_tokens=900):
    first = st.session_state.get("llm_model") or LLM_MODEL
    for model in dict.fromkeys([first, LLM_MODEL] + FALLBACK_MODELS):
        r = _chat(model, prompt, json_mode, max_tokens)
        if r.status_code == 400 and json_mode:
            r = _chat(model, prompt, False, max_tokens)  # model may not support JSON mode
        if r.status_code == 404:
            continue  # model not available on this account, try the next one
        data = _check(r)
        content = (data["choices"][0]["message"].get("content") or "").strip()
        if not content:
            raise AIError("The AI returned an empty answer. Please try again.")
        st.session_state["llm_model"] = model
        return content
    raise AIError("None of the AI models are available on this Groq account. The admin should set GROQ_LLM_MODEL.")


def parse_json(raw):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def transcribe(audio_bytes):
    r = _post(
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
def new_question(role, kind, level, asked, boss=False):
    avoid = "; ".join(asked[-5:]) or "none"
    hard = " Make it a hard, boss-level question that tests depth and real experience." if boss else ""
    q = ask_llm(
        f"Ask ONE {kind} interview question for a {level} {role} candidate.{hard} "
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


def analyze(question, answer, stats, role, kind, key_points=""):
    raw = ask_llm(
        f"""You are a strict but kind interview coach for a {role} {kind} interview.
Question: {question}
Candidate's spoken answer (transcript): {answer}
Delivery stats: {stats}
{("The answer should cover these key points: " + key_points + ". Say which ones were covered and list the ones that were missed under 'missing'.") if key_points.strip() else ""}
If the answer contains factual mistakes, point them out under "missing".

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
    data = parse_json(raw)
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


# ---------------- Voice (the browser reads text aloud, free) ----------------
def speak_button(text, label="🔊 Read aloud"):
    # The text goes into the page only as a JSON string with every "<" escaped, so it can never close the script.
    safe = json.dumps(str(text)).replace("<", "\\u003c")
    page = f"""
<button id="b" style="background:#131A2B;color:#E8ECF8;border:2px solid #00E5FF;border-radius:10px;
        padding:8px 14px;font-size:15px;cursor:pointer">{html.escape(label)}</button>
<script>
const text = {safe};
const btn = document.getElementById('b');
btn.onclick = () => {{
  const s = window.speechSynthesis;
  if (!s) {{ btn.textContent = 'Voice is not supported in this browser'; return; }}
  if (s.speaking) {{ s.cancel(); return; }}
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'en-IN'; u.rate = 0.95;
  const voices = s.getVoices();
  const v = voices.find(x => x.lang === 'en-IN') || voices.find(x => x.lang.startsWith('en'));
  if (v) u.voice = v;
  s.speak(u);
}};
</script>"""
    if hasattr(st, "iframe"):  # newer Streamlit
        st.iframe(page, height=56)
    else:
        components.html(page, height=56)


# ---------------- Login ----------------
def secret_admins():
    """Admin accounts live in the USERS_JSON secret (made with add_user.py)."""
    raw = secret("USERS_JSON")
    try:
        data = json.loads(raw) if raw else {}
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def authenticate(username, password):
    """Return the account dict, or None for a wrong ID or password. Raises DBError if the database is down."""
    u = username.strip().lower()
    rec = secret_admins().get(u)
    if rec:
        ok = verify_password(password, rec.get("salt", ""), rec.get("hash", ""))
        return {"username": u, "name": u, "role": "admin"} if ok else None
    if db_configured():
        row = get_user(u)
        if row is None:
            verify_password(password, "00" * 16, "00" * 32)  # keep the timing similar for unknown IDs
            return None
        if row.get("active", True) and verify_password(password, row["salt"], row["hash"]):
            return {"username": u, "name": row.get("name") or u, "role": "student"}
    return None


if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.fails = 0

if st.session_state.user is None:
    st.markdown(art.hero_html(APP_NAME, TAGLINE), unsafe_allow_html=True)
    st.subheader("Sign in")
    st.caption("Use the ID and password your teacher gave you. Your scores and the text of your answers are saved "
               "so your teachers can follow your progress. Your voice recordings are never stored.")
    if st.session_state.fails >= 5:
        st.error("Too many failed attempts. Please contact your teacher.")
        st.stop()
    with st.form("login"):
        u = st.text_input("User ID")
        p = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        try:
            acct = authenticate(u, p)
        except DBError as e:
            st.error(str(e))
            st.stop()
        if acct:
            st.session_state.user = acct["username"]
            st.session_state.name = acct["name"]
            st.session_state.account_role = acct["role"]
            if acct["role"] == "student":
                touch_login(acct["username"])
            st.rerun()
        else:
            st.session_state.fails += 1
            time.sleep(1)
            st.error("Wrong ID or password.")
    st.stop()

# ---------------- Game helpers ----------------
OTHER_ROLE = "Other (type my own)"
ROLE_PRESETS = [
    "Unity Game Developer",
    "Game Programmer",
    "AR/VR Developer",
    "Technical Artist",
    "3D Artist",
    "Software Developer",
    OTHER_ROLE,
]
TITLES = ["Rookie", "Apprentice", "Challenger", "Veteran", "Hero", "Legend"]
ALL_BADGES = ["🩸 First Blood", "🔥 Combo x3", "⭐ Flawless", "⚔️ Boss Slayer", "🧼 Clean Speaker", "🎯 Perfect Pace"]

is_admin = st.session_state.account_role == "admin"
for _k, _v in {"xp": 0, "streak": 0, "best_streak": 0, "badges": [], "history": [], "question_boss": False,
               "used_today": 0, "bank_idx": 0}.items():
    st.session_state.setdefault(_k, _v)


def load_saved_progress():
    ss = st.session_state
    if ss.get("progress_loaded"):
        return
    ss.progress_loaded = True
    if not db_configured():
        return
    try:
        p = load_progress(ss.user)
        if p:
            ss.xp = int(p.get("xp") or 0)
            ss.streak = int(p.get("streak") or 0)
            ss.best_streak = int(p.get("best_streak") or 0)
            ss.badges = [b for b in ALL_BADGES if b in (p.get("badges") or [])]
        ss.history = recent_scores(ss.user, 30)
        if not is_admin:
            ss.used_today = count_today(ss.user)
    except DBError as e:
        st.warning(f"Couldn't load your saved progress. {e}")


def level_info(xp):
    level = xp // 100 + 1
    return level, TITLES[min(level - 1, len(TITLES) - 1)], xp % 100


def grade_for(score):
    return "S" if score >= 9 else "A" if score == 8 else "B" if score >= 6 else "C" if score >= 4 else "D"


def earned_badges(score, stats, boss, streak, answers):
    out = []
    if answers == 1:
        out.append("🩸 First Blood")
    if streak >= 3:
        out.append("🔥 Combo x3")
    if score >= 9:
        out.append("⭐ Flawless")
    if boss and score >= 7:
        out.append("⚔️ Boss Slayer")
    if stats["filler_count"] <= 1 and stats["duration_sec"] >= 15:
        out.append("🧼 Clean Speaker")
    if 110 <= stats["wpm"] <= 170 and stats["long_pauses"] <= 1 and stats["duration_sec"] >= 15:
        out.append("🎯 Perfect Pace")
    return out


def draw_panel():
    level, title, into = level_info(st.session_state.xp)
    with game_panel.container():
        st.markdown(art.level_html(level, title), unsafe_allow_html=True)
        st.progress(into / 100)
        st.caption(f"{st.session_state.xp} XP · {100 - into} XP to next level")
        st.markdown(f"🔥 Streak **{st.session_state.streak}** · best **{st.session_state.best_streak}**")
        if st.session_state.badges:
            st.caption("Badges: " + " · ".join(st.session_state.badges))
        if not is_admin and db_configured():
            st.caption(f"Answers today: {st.session_state.used_today} of {DAILY_LIMIT}")


# ---------------- Main app ----------------
st.markdown(art.hero_html(APP_NAME, TAGLINE), unsafe_allow_html=True)

with st.sidebar:
    st.write(f"Signed in as **{st.session_state.name}**")
    if st.button("Sign out"):
        st.session_state.clear()
        st.rerun()
    mode = "Practice"
    if is_admin:
        mode = st.radio("Mode", ["Practice", "Teacher panel"], key="mode")

if mode == "Teacher panel":
    render_admin(st.session_state.user)
    st.stop()

load_saved_progress()

bank = []
if db_configured():
    try:
        bank = list_questions_cached()
    except DBError as e:
        st.sidebar.warning(f"The question bank is unavailable. {e}")
sources = (["Question bank"] if bank else []) + ["Take-Your-Test", "My own questions"]

with st.sidebar:
    game_panel = st.empty()
    source = st.radio("Question source", sources)
    cat_choice = "All"
    boss = False
    if source == "Question bank":
        cats = sorted({(q.get("category") or "General") for q in bank})
        cat_choice = st.selectbox("Category", ["All"] + cats)
        role, kind, level = "BCA student", "interview", "fresher"
    else:
        if source == "Take-Your-Test":
            boss = st.toggle("⚔️ Boss round (harder questions)")
        role_choice = st.selectbox("Role", ROLE_PRESETS)
        if role_choice == OTHER_ROLE:
            role = st.text_input("Type your role", placeholder="e.g. Web Developer").strip() or "Software Developer"
        else:
            role = role_choice
        kind = st.selectbox("Interview type", ["HR", "Behavioral", "Technical", "Mixed"])
        level = st.selectbox("Level", ["fresher", "junior", "mid-level", "senior"])

draw_panel()

if "asked" not in st.session_state:
    st.session_state.asked = []
    st.session_state.question = None
    st.session_state.my_questions = []
    st.session_state.my_idx = 0
    st.session_state.q_text = ""


def make_question():
    try:
        q = new_question(role, kind, level, st.session_state.asked, boss)
    except (AIError, requests.RequestException) as e:
        st.error(str(e))
        st.stop()
    st.session_state.question = q
    st.session_state.question_boss = boss
    st.session_state.asked.append(q)


key_points = ""
is_boss = False
question_id = None
src_tag = "ai"

if source == "Question bank":
    src_tag = "bank"
    pool = [q for q in bank if cat_choice == "All" or (q.get("category") or "General") == cat_choice]
    if not pool:
        st.info("There are no questions in this category yet.")
        st.stop()
    idx = min(st.session_state.bank_idx, len(pool) - 1)
    c_prev, c_next, c_rand, c_info = st.columns([1, 1, 1, 2])
    if c_prev.button("◀ Previous") and idx > 0:
        st.session_state.bank_idx = idx - 1
        st.rerun()
    if c_next.button("Next ▶") and idx < len(pool) - 1:
        st.session_state.bank_idx = idx + 1
        st.rerun()
    if c_rand.button("🎲 Random") and len(pool) > 1:
        st.session_state.bank_idx = random.choice([i for i in range(len(pool)) if i != idx])
        st.rerun()
    c_info.caption(f"Quest {idx + 1} of {len(pool)}")
    chosen = pool[idx]
    question = chosen["text"]
    key_points = chosen.get("key_points") or ""
    question_id = chosen["id"]
    kind = chosen.get("category") or "interview"
    audio_key = f"audio_bank_{question_id}"
elif source == "AI-generated":
    if st.button("🎲 New quest") or st.session_state.question is None:
        with st.spinner("Rolling a new quest..."):
            make_question()
    question = st.session_state.question
    is_boss = st.session_state.question_boss
    audio_key = f"audio_ai_{len(st.session_state.asked)}"
else:
    src_tag = "mine"
    with st.expander("Add or edit my quests", expanded=not st.session_state.my_questions):
        st.text_area("One question per line", key="q_text", height=160)
        if st.button("Save questions"):
            st.session_state.my_questions = [
                q.strip() for q in st.session_state.q_text.splitlines() if q.strip()
            ]
            st.session_state.my_idx = 0
            st.rerun()
    qs = st.session_state.my_questions
    if not qs:
        st.info("Type your questions above (one per line), then click **Save questions**.")
        st.stop()
    idx = min(st.session_state.my_idx, len(qs) - 1)
    c_prev, c_next, c_info = st.columns([1, 1, 3])
    if c_prev.button("◀ Previous") and idx > 0:
        st.session_state.my_idx = idx - 1
        st.rerun()
    if c_next.button("Next ▶") and idx < len(qs) - 1:
        st.session_state.my_idx = idx + 1
        st.rerun()
    c_info.caption(f"Quest {idx + 1} of {len(qs)}")
    question = qs[idx]
    audio_key = f"audio_my_{idx}"

tag = "⚔️ BOSS ROUND" if is_boss else "QUEST"
st.markdown(
    f'<div class="quest"><div class="tag">{tag}</div>{html.escape(question)}</div>',
    unsafe_allow_html=True,
)
speak_button(question, "🔊 Read the question aloud")

if source == "My own questions":
    key_points = st.text_area(
        "Key points a good answer should cover (optional)",
        key=f"kp_{idx}",
        placeholder="e.g. mention object pooling, Update vs FixedUpdate, a real example",
        height=90,
    )

audio = st.audio_input("🎙️ Record your answer", key=audio_key)

if audio and st.button("⚔️ Submit answer"):
    if not is_admin and db_configured() and st.session_state.used_today >= DAILY_LIMIT:
        st.warning(f"You have used all {DAILY_LIMIT} answers for today. Come back tomorrow!")
        st.stop()
    try:
        with st.spinner("Transcribing..."):
            text, words = transcribe(audio.getvalue())
        if not text:
            st.warning("Couldn't hear anything. Try recording again.")
            st.stop()
        stats = delivery_stats(words)
        with st.spinner("The judges are scoring..."):
            fb = analyze(question, text, stats, role, kind, key_points)
    except AIError as e:
        st.error(str(e))
        st.stop()
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        st.error(f"Something went wrong, please try again. ({type(e).__name__})")
        st.stop()

    # ---- game bookkeeping
    score = fb["score"]
    old_level = level_info(st.session_state.xp)[0]
    st.session_state.streak = st.session_state.streak + 1 if score >= 7 else 0
    st.session_state.best_streak = max(st.session_state.best_streak, st.session_state.streak)
    gain = score * 10 + (20 if is_boss else 0) + (10 if st.session_state.streak >= 3 else 0)
    st.session_state.xp += gain
    st.session_state.history.append(score)
    st.session_state.used_today += 1
    new_badges = [
        b for b in earned_badges(score, stats, is_boss, st.session_state.streak, len(st.session_state.history))
        if b not in st.session_state.badges
    ]
    st.session_state.badges.extend(new_badges)
    new_level = level_info(st.session_state.xp)[0]
    g = grade_for(score)

    # ---- save to the database (the result is still shown if this fails)
    if db_configured():
        try:
            save_progress(st.session_state.user, st.session_state.xp, st.session_state.streak,
                          st.session_state.best_streak, st.session_state.badges)
            add_attempt(username=st.session_state.user, question=question, question_id=question_id,
                        source=src_tag, score=score, xp=gain, grade=g, wpm=stats["wpm"],
                        fillers=stats["filler_count"], pauses=stats["long_pauses"],
                        transcript=text, feedback=fb)
        except DBError as e:
            st.warning(f"Your result could not be saved. {e}")

    # ---- results
    st.markdown(art.trophy_html("Quest complete!"), unsafe_allow_html=True)
    r1, r2, r3 = st.columns(3)
    r1.markdown(f'<div class="grade grade-{g}">{g}</div><div class="gcap">RANK</div>', unsafe_allow_html=True)
    r2.metric("Score", f"{score}/10")
    r3.metric("XP earned", f"+{gain}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Pace (words/min)", stats["wpm"])
    c2.metric("Filler words", stats["filler_count"])
    c3.metric("Long pauses", stats["long_pauses"])

    st.markdown("### Your transcript")
    st.write(text)
    st.markdown("### 💪 Strengths")
    for s_ in fb["strengths"]:
        st.write(f"- {s_}")
    st.markdown("### 🗺️ Missed loot (what was missing)")
    for m_ in fb["missing"]:
        st.write(f"- {m_}")
    st.markdown("### Structure")
    st.write(fb["structure_feedback"])
    st.markdown("### Delivery")
    st.write(fb["delivery_feedback"])
    st.markdown("### 💡 Stronger version")
    st.info(fb["improved_answer"])
    spoken = f"Your score is {score} out of 10. " + " ".join(
        ["What was missing: " + ". ".join(fb["missing"]) + "."] if fb["missing"] else []
    ) + " " + fb["delivery_feedback"]
    speak_button(spoken, "🔊 Read my feedback aloud")

    for b_ in new_badges:
        st.toast(f"Badge unlocked: {b_}", icon="🏅")
    if new_level > old_level:
        st.balloons()
        st.toast(f"LEVEL UP! You are now level {new_level}", icon="🆙")
    draw_panel()

if st.session_state.history:
    st.sidebar.markdown("### Score history")
    st.sidebar.line_chart(st.session_state.history)
