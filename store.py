"""Session data store: starts EMPTY (all KPIs = 0). Files uploaded by the user are loaded
into an in-memory SQLite DB, so every dashboard number comes from a real SQL query."""
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

BASE = Path(__file__).parent

SCHEMA = {
    "patients": ["patient_id", "first_name", "last_name", "gender", "date_of_birth", "contact_number", "address",
                 "registration_date", "insurance_provider", "insurance_number", "email"],
    "doctors": ["doctor_id", "first_name", "last_name", "specialization", "phone_number", "years_experience",
                "hospital_branch", "email"],
    "appointments": ["appointment_id", "patient_id", "doctor_id", "appointment_date", "appointment_time",
                     "reason_for_visit", "status"],
    "treatments": ["treatment_id", "appointment_id", "treatment_type", "description", "cost", "treatment_date"],
    "billing": ["bill_id", "patient_id", "treatment_id", "bill_date", "amount", "payment_method", "payment_status"],
}
KEYS = {"patients": "patient_id", "doctors": "doctor_id", "appointments": "appointment_id",
        "treatments": "treatment_id", "billing": "bill_id"}
DATE_COLS = {"patients": ["date_of_birth", "registration_date"], "appointments": ["appointment_date"],
             "treatments": ["treatment_date"], "billing": ["bill_date"]}
TIME_COLS = {"appointments": ["appointment_time"]}
NUM_COLS = {"doctors": ["years_experience"], "treatments": ["cost"], "billing": ["amount"]}
TITLE_COLS = {"appointments": ["status"], "billing": ["payment_status"]}
KEYWORDS = {"patients": "patient", "doctors": "doctor", "appointments": "appoint", "treatments": "treat",
            "billing": "bill"}
ORDER = list(SCHEMA)

VIEW_SQL = """
CREATE VIEW v_appt AS
SELECT a.appointment_id, a.patient_id,
       TRIM(COALESCE(p.first_name,'')||' '||COALESCE(p.last_name,'')) AS patient_name, p.gender,
       CAST((julianday(a.appointment_date)-julianday(p.date_of_birth))/365.25 AS INTEGER) AS age,
       COALESCE(NULLIF(p.insurance_provider,''),'Self-pay') AS insurance_provider,
       a.doctor_id, 'Dr. '||TRIM(COALESCE(d.first_name,'')||' '||COALESCE(d.last_name,'')) AS doctor_name,
       COALESCE(d.specialization,'Unknown') AS specialization, COALESCE(d.hospital_branch,'Unknown') AS branch,
       d.years_experience,
       a.appointment_date, a.appointment_time,
       CAST(substr(a.appointment_time,1,2) AS INTEGER) AS hour,
       substr(a.appointment_date,1,7) AS month,
       CAST(strftime('%w',a.appointment_date) AS INTEGER) AS dow,
       a.reason_for_visit AS reason, COALESCE(a.status,'Unknown') AS status,
       t.treatment_id, COALESCE(t.treatment_type,'None') AS treatment_type, COALESCE(t.cost,0) AS cost,
       b.bill_id, b.bill_date, COALESCE(b.amount,0) AS amount, b.payment_method,
       COALESCE(b.payment_status,'No bill') AS payment_status
FROM appointments a
LEFT JOIN patients p ON p.patient_id = a.patient_id
LEFT JOIN doctors d ON d.doctor_id = a.doctor_id
LEFT JOIN treatments t ON t.appointment_id = a.appointment_id
LEFT JOIN billing b ON b.treatment_id = t.treatment_id
"""


def _rebuild(con):
    con.execute("DROP VIEW IF EXISTS v_appt")
    con.execute(VIEW_SQL)
    con.commit()


def conn() -> sqlite3.Connection:
    if "_con" not in st.session_state:
        con = sqlite3.connect(":memory:", check_same_thread=False)
        for t, cols in SCHEMA.items():
            nums = NUM_COLS.get(t, [])
            ddl = ", ".join(f'"{c}" {"REAL" if c in nums else "TEXT"}' for c in cols)
            con.execute(f'CREATE TABLE "{t}" ({ddl})')
        _rebuild(con)
        st.session_state["_con"] = con
        st.session_state["_ver"] = 0
        st.session_state["_seen"] = set()
        st.session_state["_log"] = []
    return st.session_state["_con"]


def version() -> int:
    conn()
    return st.session_state["_ver"]


def run(sql, params=()) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn(), params=list(params))


def counts() -> dict:
    con = conn()
    return {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in SCHEMA}


def has_data() -> bool:
    return counts()["appointments"] > 0


# ───────────── file → table ─────────────
def _norm_cols(df):
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    return df


def detect(df, filename=""):
    """Work out which table a dataframe belongs to (file/sheet name first, then column overlap)."""
    low = filename.lower()
    for t, kw in KEYWORDS.items():
        if kw in low:
            return t
    cols = set(_norm_cols(df).columns)
    score = {t: len(cols & set(c)) for t, c in SCHEMA.items()}
    best = max(score, key=score.get)
    return best if score[best] >= 3 else None


def clean(table, df):
    df = _norm_cols(df)
    for c in SCHEMA[table]:
        if c not in df.columns:
            df[c] = None
    df = df[SCHEMA[table]].copy()
    for c in DATE_COLS.get(table, []):
        df[c] = pd.to_datetime(df[c], errors="coerce", format="mixed").dt.strftime("%Y-%m-%d")
    for c in TIME_COLS.get(table, []):
        df[c] = pd.to_datetime(df[c].astype("string"), errors="coerce", format="mixed").dt.strftime("%H:%M:%S")
    for c in NUM_COLS.get(table, []):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in TITLE_COLS.get(table, []):
        df[c] = df[c].astype("string").str.strip().str.capitalize()
    for c in df.columns:
        if c not in NUM_COLS.get(table, []):
            df[c] = df[c].astype("string").str.strip() if c not in DATE_COLS.get(table, []) + TIME_COLS.get(table, []) else df[c]
    df = df.dropna(subset=[KEYS[table]]).drop_duplicates(subset=[KEYS[table]], keep="last")
    return df.astype(object).where(df.notna(), None)


def load(table, df, mode="replace") -> int:
    con = conn()
    new = clean(table, df)
    if mode == "merge":
        old = pd.read_sql_query(f'SELECT * FROM "{table}"', con)
        new = pd.concat([old, new]).drop_duplicates(subset=[KEYS[table]], keep="last")
    con.execute("DROP VIEW IF EXISTS v_appt")
    con.execute(f'DELETE FROM "{table}"')
    new.to_sql(table, con, if_exists="append", index=False)
    _rebuild(con)
    st.session_state["_ver"] += 1
    return len(new)


def ingest(upload, mode="replace") -> list[str]:
    """Accepts a Streamlit UploadedFile (csv / xlsx / xls, multi-sheet ok). Returns log lines."""
    out = []
    try:
        if upload.name.lower().endswith(".csv"):
            frames = {upload.name: pd.read_csv(upload, dtype=str, encoding="utf-8-sig")}
        else:
            frames = pd.read_excel(upload, dtype=str, sheet_name=None)
            frames = {f"{upload.name}:{k}": v for k, v in frames.items()}
    except Exception as e:  # noqa: BLE001
        return [f"❌ {upload.name}: could not read ({e})"]
    for label, df in frames.items():
        t = detect(df, label)
        if not t:
            out.append(f"⚠️ {label}: could not tell which table this is — rename file to patients/doctors/appointments/treatments/billing")
            continue
        n = load(t, df, mode)
        miss = [c for c in SCHEMA[t] if c not in _norm_cols(df).columns]
        out.append(f"✅ {label} → **{t}** ({n} rows)" + (f" — missing columns: {', '.join(miss)}" if miss else ""))
    return out


def load_sample() -> list[str]:
    out = []
    for t in ORDER:
        f = BASE / "Dataset" / f"{t}.csv"
        if f.exists():
            n = load(t, pd.read_csv(f, dtype=str, encoding="utf-8-sig"))
            out.append(f"✅ sample {t} ({n} rows)")
    return out or ["⚠️ Dataset folder not found"]


def clear_all():
    con = conn()
    con.execute("DROP VIEW IF EXISTS v_appt")
    for t in SCHEMA:
        con.execute(f'DELETE FROM "{t}"')
    _rebuild(con)
    st.session_state["_ver"] += 1
    st.session_state["_seen"] = set()
    st.session_state["_log"] = []
