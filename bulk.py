"""Reading bulk files (question lists, student lists). No Streamlit in here, so it is easy to test."""
import csv
import io
import re

MAX_ROWS = 5000
USERNAME_RE = re.compile(r"[a-z0-9_.-]{2,32}")

Q_HEADERS = {"question", "questions", "text", "q", "interview question"}
CAT_HEADERS = {"category", "topic", "section", "type", "subject"}
KP_HEADERS = {"key points", "keypoints", "key_points", "points", "expected", "keywords", "answer", "key"}

ID_HEADERS = {"username", "user", "id", "userid", "user id", "roll", "roll no", "roll number", "rollno",
              "reg no", "regno", "register number", "register no", "registration number", "student id"}
NAME_HEADERS = {"name", "student name", "full name", "student"}
PW_HEADERS = {"password", "pass", "pwd"}


def clean_username(value):
    u = re.sub(r"\s+", "", str(value or "")).lower()
    return u if USERNAME_RE.fullmatch(u) else None


def _s(cell):
    if cell is None:
        return ""
    if isinstance(cell, float) and cell.is_integer():
        return str(int(cell))
    return re.sub(r"\s+", " ", str(cell)).strip()


def _decode(raw):
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def read_rows(raw, filename):
    """Return a list of rows (lists of strings) from .xlsx, .csv or plain text (one item per line)."""
    name = (filename or "").lower()
    if name.endswith(".xlsx"):
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        rows = [[_s(c) for c in row] for row in wb.active.iter_rows(values_only=True)]
    else:
        text = _decode(raw)
        if name.endswith(".csv"):
            first = text.splitlines()[0] if text.strip() else ""
            delim = "\t" if "\t" in first else ";" if first.count(";") > first.count(",") else ","
            rows = [[_s(c) for c in r] for r in csv.reader(io.StringIO(text), delimiter=delim)]
        else:
            rows = [[_s(line)] for line in text.splitlines()]
    rows = [r for r in rows if any(r)]
    return rows[: MAX_ROWS + 1]


def _find(header, names):
    for i, cell in enumerate(header):
        if cell.strip().lower() in names:
            return i
    return None


def _cell(row, i):
    return row[i] if i is not None and i < len(row) else ""


def parse_questions(raw, filename, default_category="General"):
    """Return (questions, skipped). Each question is {"text", "category", "key_points"}."""
    rows = read_rows(raw, filename)
    qi, ci, ki = 0, None, None
    if rows:
        header_q = _find(rows[0], Q_HEADERS)
        if header_q is not None:
            qi, ci, ki = header_q, _find(rows[0], CAT_HEADERS), _find(rows[0], KP_HEADERS)
            rows = rows[1:]
        else:
            wide = max((len(r) for r in rows), default=1)
            ci = 1 if wide >= 2 else None
            ki = 2 if wide >= 3 else None
    out, seen, skipped = [], set(), 0
    for r in rows:
        text = _cell(r, qi)
        if not (6 <= len(text) <= 600) or text.lower() in seen:
            skipped += 1
            continue
        seen.add(text.lower())
        out.append({
            "text": text,
            "category": (_cell(r, ci) or default_category or "General")[:60],
            "key_points": _cell(r, ki)[:600],
        })
    return out[:MAX_ROWS], skipped


def parse_students(raw, filename):
    """Return (students, problems). Each student is {"username", "name", "password"} (password may be '')."""
    rows = read_rows(raw, filename)
    ii, ni, pi = 0, 1, 2
    start = 1
    if rows:
        h = _find(rows[0], ID_HEADERS)
        if h is not None:
            ii, ni, pi = h, _find(rows[0], NAME_HEADERS), _find(rows[0], PW_HEADERS)
        else:
            start = 0
    out, problems, seen = [], [], set()
    for n, r in enumerate(rows[start:], start=start + 1):
        raw_id = _cell(r, ii)
        u = clean_username(raw_id)
        if not u:
            problems.append(f"Row {n}: '{raw_id}' is not a valid ID (2 to 32 letters, numbers, _ . -).")
            continue
        if u in seen:
            problems.append(f"Row {n}: '{u}' appears twice, the second one was skipped.")
            continue
        pw = _cell(r, pi)
        if pw and len(pw) < 6:
            problems.append(f"Row {n}: the password for '{u}' is shorter than 6 characters.")
            continue
        seen.add(u)
        out.append({"username": u, "name": _cell(r, ni)[:80], "password": pw})
    return out[:MAX_ROWS], problems
