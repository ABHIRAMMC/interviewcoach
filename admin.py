"""Teacher panel for ARticulate: students, question bank and results."""
import csv
import io
from datetime import datetime

import streamlit as st

import art
from bulk import clean_username, parse_questions, parse_students
from db import (DBConflict, DBError, IST, db, add_questions, all_progress, attempts_overview, clear_questions,
                create_user, create_users_bulk, delete_questions, delete_student, existing_usernames,
                hash_password, list_questions, list_students, new_password, set_active, set_password,
                student_attempts)


def _csv_bytes(rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")  # utf-8-sig so Excel opens it correctly


def fmt_ts(value):
    if not value:
        return ""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(IST).strftime("%d %b %Y %H:%M")
    except ValueError:
        return str(value)


# ---------------- students ----------------
def students_tab():
    st.markdown(art.section_title("students", "Students", "accounts, passwords, access"), unsafe_allow_html=True)
    st.subheader("Add one student")
    with st.form("add_one", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        uid = c1.text_input("Student ID (for example roll number)")
        name = c2.text_input("Full name")
        pw = c3.text_input("Password (leave empty to generate one)")
        go = st.form_submit_button("Create account")
    if go:
        u = clean_username(uid)
        if not u:
            st.error("The ID must be 2 to 32 characters: letters, numbers, _ . -")
        elif pw and len(pw) < 6:
            st.error("The password must have at least 6 characters.")
        else:
            password = pw or new_password()
            try:
                create_user(u, name.strip(), password)
                st.success(f"Created **{u}**. Password: `{password}`. Copy it now, it can't be shown again.")
            except DBConflict:
                st.error("That ID already exists.")

    st.subheader("Add many students")
    st.caption("Upload a CSV or Excel file with three columns, in this order: **1) ID or roll number, 2) name, "
               "3) password**. A heading row is fine. If a password cell is empty, a password is generated for that student.")
    up = st.file_uploader("Student list", type=["csv", "xlsx"], key="students_file")
    if up is not None:
        students, problems = parse_students(up.getvalue(), up.name)
        st.write(f"Found **{len(students)}** valid students.")
        for p in problems[:10]:
            st.warning(p)
        if len(problems) > 10:
            st.caption(f"...and {len(problems) - 10} more problems.")
        if students:
            st.dataframe([{"ID": s["username"], "Name": s["name"],
                            "Password": "from the file" if s["password"] else "will be generated"}
                           for s in students[:200]], hide_index=True)
            if st.button("Create these accounts", key="create_bulk"):
                existing = existing_usernames()
                rows, created, skipped = [], [], []
                with st.spinner("Creating accounts..."):
                    for s in students:
                        if s["username"] in existing:
                            skipped.append(s["username"])
                            continue
                        pw = s["password"] or new_password()
                        salt, h = hash_password(pw)
                        rows.append({"username": s["username"], "name": s["name"], "salt": salt, "hash": h,
                                     "role": "student"})
                        created.append({"username": s["username"], "name": s["name"], "password": pw})
                    if rows:
                        create_users_bulk(rows)
                st.session_state["new_credentials"] = created
                st.success(f"Created {len(created)} accounts." + (f" Skipped {len(skipped)} that already exist." if skipped else ""))

    creds = st.session_state.get("new_credentials")
    if creds:
        st.info("Download this list now and give each student their own ID and password. "
                "Passwords are stored only in scrambled form, so they can't be shown again.")
        st.dataframe(creds, hide_index=True)
        st.download_button("⬇️ Download credentials (CSV)", _csv_bytes(creds, ["username", "name", "password"]),
                           file_name="student-credentials.csv", mime="text/csv")
        if st.button("Hide this list", key="hide_creds"):
            st.session_state.pop("new_credentials", None)
            st.rerun()

    st.subheader("Manage students")
    students = list_students()
    if not students:
        st.info("No students yet.")
        return
    st.dataframe([{"ID": s["username"], "Name": s["name"], "Active": s["active"],
                   "Last sign-in": fmt_ts(s["last_login"])} for s in students], hide_index=True)
    pick = st.selectbox("Select a student", [s["username"] for s in students], key="manage_pick")
    rec = next(s for s in students if s["username"] == pick)
    c1, c2, c3 = st.columns(3)
    if c1.button("🔑 Reset password", key="reset_pw"):
        pw = new_password()
        set_password(pick, pw)
        st.success(f"New password for **{pick}**: `{pw}`. Copy it now.")
    if c2.button("⏸ Deactivate" if rec["active"] else "▶ Activate", key="toggle_active"):
        set_active(pick, not rec["active"])
        st.rerun()
    with c3:
        sure = st.checkbox("Yes, delete this student and all their results", key="confirm_delete")
        if st.button("🗑 Delete student", key="delete_student") and sure:
            delete_student(pick)
            st.rerun()


# ---------------- question bank ----------------
def _add_new(qs, who):
    have = {q["text"].strip().lower() for q in list_questions()}
    fresh = [q for q in qs if q["text"].strip().lower() not in have]
    if fresh:
        add_questions(fresh, created_by=who)
    return len(fresh), len(qs) - len(fresh)


def bank_tab(who):
    st.markdown(art.section_title("bank", "Question bank", "bulk upload and editing"), unsafe_allow_html=True)
    st.subheader("Add questions in bulk")
    st.caption("CSV or Excel file with the columns: question, category (optional), key points (optional). "
               "A plain text file with one question per line also works. Key points are never shown to students; "
               "they are only used to check the answers.")
    default_cat = st.text_input("Category for questions that have none", "General", key="bank_default_cat")
    up = st.file_uploader("Question file", type=["csv", "xlsx", "txt"], key="bank_file")
    if up is not None:
        qs, skipped = parse_questions(up.getvalue(), up.name, default_cat.strip() or "General")
        st.write(f"Found **{len(qs)}** questions" + (f" ({skipped} skipped: empty, too short or repeated)." if skipped else "."))
        if qs:
            st.dataframe(qs[:10], hide_index=True)
            if st.button("Add these to the question bank", key="bank_add_file"):
                added, dup = _add_new(qs, who)
                st.success(f"Added {added} questions." + (f" {dup} were already in the bank." if dup else ""))

    with st.expander("Or paste questions here"):
        pasted = st.text_area("One question per line", key="bank_paste", height=140)
        cat = st.text_input("Category", "General", key="bank_paste_cat")
        if st.button("Add pasted questions", key="bank_add_paste"):
            qs, _ = parse_questions(pasted.encode("utf-8"), "pasted.txt", cat.strip() or "General")
            if qs:
                added, dup = _add_new(qs, who)
                st.success(f"Added {added} questions." + (f" {dup} were already in the bank." if dup else ""))
            else:
                st.warning("Nothing to add.")

    st.subheader("Current question bank")
    allq = list_questions()
    if not allq:
        st.info("The question bank is empty. Students can still use AI questions and their own questions.")
        return
    cats = sorted({q["category"] or "General" for q in allq})
    cat_f = st.selectbox("Show category", ["All"] + cats, key="bank_cat_filter")
    shown = [q for q in allq if cat_f == "All" or (q["category"] or "General") == cat_f]
    st.caption(f"{len(shown)} of {len(allq)} questions")
    st.dataframe([{"ID": q["id"], "Category": q["category"], "Question": q["text"], "Key points": q["key_points"]}
                  for q in shown[:500]], hide_index=True)
    by_id = {q["id"]: q for q in shown}
    pick = st.multiselect("Select questions to delete", list(by_id),
                          format_func=lambda i: f"{i}: {by_id[i]['text'][:70]}", key="bank_delete_pick")
    if pick and st.button("Delete selected questions", key="bank_delete"):
        delete_questions(pick)
        st.rerun()
    with st.expander("Danger zone"):
        sure = st.checkbox("Yes, delete the whole question bank", key="bank_clear_confirm")
        if st.button("Delete ALL questions", key="bank_clear") and sure:
            clear_questions()
            st.rerun()


# ---------------- results ----------------
def results_tab():
    students = {s["username"]: s for s in list_students()}
    stats = {}
    for a in attempts_overview():
        d = stats.setdefault(a["username"], {"n": 0, "sum": 0, "best": 0, "last": ""})
        d["n"] += 1
        d["sum"] += int(a["score"])
        d["best"] = max(d["best"], int(a["score"]))
        d["last"] = max(d["last"], a["created_at"])
    xp = {p["username"]: p["xp"] for p in all_progress()}
    names = sorted(set(students) | set(stats))
    st.markdown(art.section_title("results", "Results", f"{len(names)} student{'s' if len(names) != 1 else ''}"),
                unsafe_allow_html=True)
    if not names:
        st.info("No results yet. They appear here as soon as students answer questions.")
        return
    rows = []
    for u in names:
        d = stats.get(u, {"n": 0, "sum": 0, "best": 0, "last": ""})
        rows.append({"ID": u, "Name": students.get(u, {}).get("name", ""), "Answers": d["n"],
                     "Average score": round(d["sum"] / d["n"], 1) if d["n"] else None,
                     "Best score": d["best"] if d["n"] else None, "XP": xp.get(u, 0),
                     "Last practice": fmt_ts(d["last"])})
    st.dataframe(rows, hide_index=True)
    st.download_button("⬇️ Download results (CSV)",
                       _csv_bytes(rows, ["ID", "Name", "Answers", "Average score", "Best score", "XP", "Last practice"]),
                       file_name="articulate-results.csv", mime="text/csv")

    st.subheader("A student's recent answers")
    pick = st.selectbox("Student", names, key="results_pick")
    attempts = student_attempts(pick, 50)
    if not attempts:
        st.info("This student hasn't answered anything yet.")
        return
    st.dataframe([{"When": fmt_ts(a["created_at"]), "Question": a["question"], "Score": a["score"],
                   "Grade": a.get("grade"), "Pace (wpm)": a.get("wpm"), "Fillers": a.get("fillers")}
                  for a in attempts], hide_index=True)
    for a in attempts[:10]:
        with st.expander(f"{fmt_ts(a['created_at'])} · {a['score']}/10 · {a['question'][:60]}"):
            st.markdown("**What the student said**")
            st.write(a.get("transcript") or "")
            fb = a.get("feedback") or {}
            if fb.get("missing"):
                st.markdown("**What was missing**")
                for m in fb["missing"]:
                    st.write(f"- {m}")
            if fb.get("delivery_feedback"):
                st.markdown("**Delivery**")
                st.write(fb["delivery_feedback"])


# ---------------- entry point ----------------
def render_admin(who):
    st.markdown(art.section_title("panel", "Teacher panel"), unsafe_allow_html=True)
    try:
        db("GET", "users", {"select": "username", "limit": "1"})  # connection test
        t1, t2, t3 = st.tabs(["Students", "Question bank", "Results"])
        with t1:
            students_tab()
        with t2:
            bank_tab(who)
        with t3:
            results_tab()
    except DBError as e:
        st.error(f"Database problem: {e}")
