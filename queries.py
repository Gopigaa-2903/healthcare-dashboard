"""All analytics are real SQL (joins, CTEs, window functions) over the view v_appt.
{W} is replaced by the active filters ("WHERE 1=1 AND ...")."""
import numpy as np
import pandas as pd

import store

PAID = "SUM(CASE WHEN payment_status='Paid' THEN amount ELSE 0 END)"
PEND = "SUM(CASE WHEN payment_status='Pending' THEN amount ELSE 0 END)"
FAIL = "SUM(CASE WHEN payment_status='Failed' THEN amount ELSE 0 END)"

Q = {
"kpis": f"""
SELECT COUNT(*) AS appts, COUNT(DISTINCT patient_id) AS patients, COUNT(DISTINCT doctor_id) AS doctors,
       COALESCE(SUM(status='Completed'),0) AS completed, COALESCE(SUM(status='Scheduled'),0) AS scheduled,
       COALESCE(SUM(status='Cancelled'),0) AS cancelled, COALESCE(SUM(status='No-show'),0) AS noshow,
       COALESCE({PAID},0) AS collected, COALESCE({PEND},0) AS pending, COALESCE({FAIL},0) AS failed,
       COALESCE(SUM(amount),0) AS billed
FROM v_appt {{W}}""",

"daily": f"""
SELECT appointment_date AS day, COUNT(*) AS appts, COALESCE({PAID},0) AS collected
FROM v_appt {{W}} GROUP BY appointment_date ORDER BY day""",

"monthly": f"""
WITH m AS (
  SELECT month, COUNT(*) AS appts, COALESCE({PAID},0) AS collected, COALESCE({PEND},0) AS pending,
         COALESCE({FAIL},0) AS failed, COALESCE(SUM(amount),0) AS billed
  FROM v_appt {{W}} GROUP BY month)
SELECT month, appts, collected, pending, failed, billed,
       LAG(collected) OVER (ORDER BY month) AS prev_collected,
       ROUND(100.0*(collected-LAG(collected) OVER (ORDER BY month))
             / NULLIF(LAG(collected) OVER (ORDER BY month),0),1) AS mom_pct,
       SUM(collected) OVER (ORDER BY month) AS cumulative
FROM m ORDER BY month""",

"status": """
SELECT status, COUNT(*) AS n FROM v_appt {W} GROUP BY status ORDER BY n DESC""",

"payment_status": """
SELECT payment_status, COUNT(*) AS bills, ROUND(SUM(amount),0) AS amount
FROM v_appt {W} AND bill_id IS NOT NULL GROUP BY payment_status ORDER BY amount DESC""",

"specialization": f"""
SELECT specialization, COUNT(*) AS appts, COALESCE({PAID},0) AS collected
FROM v_appt {{W}} GROUP BY specialization ORDER BY appts DESC""",

"flow": """
SELECT specialization, payment_status, ROUND(SUM(amount),0) AS amount
FROM v_appt {W} AND bill_id IS NOT NULL GROUP BY specialization, payment_status""",

"appt_list": """
SELECT appointment_id AS ID, patient_name AS Patient, doctor_name AS Doctor, specialization AS Specialization,
       branch AS Branch, appointment_date AS Date, appointment_time AS Time, reason AS Reason, status AS Status,
       treatment_type AS Treatment, amount AS Amount, payment_status AS Payment
FROM v_appt {W} ORDER BY appointment_date DESC, appointment_time""",

"heatmap": """
SELECT dow, hour, COUNT(*) AS n FROM v_appt {W} AND hour IS NOT NULL GROUP BY dow, hour""",

"doctor_scorecard": f"""
WITH d AS (
  SELECT doctor_id, doctor_name, specialization, branch, MAX(years_experience) AS experience,
         COUNT(*) AS appts, COUNT(DISTINCT patient_id) AS patients,
         SUM(status='Completed') AS completed, SUM(status='No-show') AS noshow, SUM(status='Cancelled') AS cancelled,
         COALESCE({PAID},0) AS collected, COALESCE({PEND}+{FAIL},0) AS outstanding
  FROM v_appt {{W}} GROUP BY doctor_id, doctor_name, specialization, branch)
SELECT *, ROUND(100.0*completed/appts,1) AS completion_pct,
       ROUND(100.0*(noshow+cancelled)/appts,1) AS leakage_pct,
       RANK() OVER (ORDER BY collected DESC) AS revenue_rank,
       ROUND(100.0*collected/NULLIF(SUM(collected) OVER (),0),1) AS revenue_share_pct,
       ROUND(collected*1.0/appts,0) AS revenue_per_appt
FROM d ORDER BY collected DESC""",

"treatments": f"""
SELECT treatment_type, COUNT(*) AS cases, ROUND(AVG(cost),0) AS avg_cost, ROUND(SUM(amount),0) AS billed,
       COALESCE(ROUND({PAID},0),0) AS collected,
       ROUND(100.0*COALESCE({PAID},0)/NULLIF(SUM(amount),0),1) AS collection_pct,
       RANK() OVER (ORDER BY SUM(amount) DESC) AS rev_rank
FROM v_appt {{W}} AND treatment_id IS NOT NULL GROUP BY treatment_type ORDER BY billed DESC""",

"payment_method": f"""
SELECT COALESCE(payment_method,'Unknown') AS method, COUNT(*) AS bills, ROUND(SUM(amount),0) AS billed,
       COALESCE(ROUND({PAID},0),0) AS collected
FROM v_appt {{W}} AND bill_id IS NOT NULL GROUP BY method ORDER BY billed DESC""",

"aging": """
WITH ref AS (SELECT MAX(appointment_date) AS d FROM v_appt),
o AS (
  SELECT v.*, CAST(julianday((SELECT d FROM ref)) - julianday(bill_date) AS INTEGER) AS age_days
  FROM v_appt v {W} AND payment_status IN ('Pending','Failed') AND bill_date IS NOT NULL)
SELECT CASE WHEN age_days <= 30 THEN '0-30 days' WHEN age_days <= 90 THEN '31-90 days'
            WHEN age_days <= 180 THEN '91-180 days' ELSE '180+ days' END AS bucket,
       payment_status, COUNT(*) AS bills, ROUND(SUM(amount),0) AS amount
FROM o GROUP BY bucket, payment_status""",

"double_booking": """
SELECT doctor_name, appointment_date, appointment_time, COUNT(*) AS bookings,
       GROUP_CONCAT(patient_name, ' | ') AS patients
FROM v_appt {W} AND status <> 'Cancelled'
GROUP BY doctor_id, doctor_name, appointment_date, appointment_time HAVING COUNT(*) > 1
ORDER BY appointment_date""",

"patients360": f"""
SELECT patient_id, patient_name, gender, MAX(age) AS age, insurance_provider, COUNT(*) AS visits,
       SUM(status='Completed') AS completed, MIN(appointment_date) AS first_visit, MAX(appointment_date) AS last_visit,
       ROUND(SUM(amount),0) AS billed, COALESCE(ROUND({PAID},0),0) AS paid,
       COALESCE(ROUND({PEND}+{FAIL},0),0) AS outstanding,
       DENSE_RANK() OVER (ORDER BY SUM(amount) DESC) AS value_rank
FROM v_appt {{W}} GROUP BY patient_id, patient_name, gender, insurance_provider ORDER BY billed DESC""",

"age_group": f"""
SELECT CASE WHEN age < 18 THEN '0-17' WHEN age < 35 THEN '18-34' WHEN age < 50 THEN '35-49'
            WHEN age < 65 THEN '50-64' ELSE '65+' END AS age_group,
       COUNT(*) AS appts, COALESCE(ROUND({PAID},0),0) AS collected
FROM v_appt {{W}} AND age IS NOT NULL GROUP BY age_group ORDER BY age_group""",

"reasons": """
SELECT COALESCE(reason,'Unknown') AS reason, COUNT(*) AS n,
       ROUND(100.0*SUM(status IN ('Cancelled','No-show'))/COUNT(*),1) AS leakage_pct
FROM v_appt {W} GROUP BY reason ORDER BY n DESC""",

"dq_orphans": """
SELECT 'appointments → unknown patient' AS issue, COUNT(*) AS rows FROM appointments WHERE patient_id NOT IN (SELECT patient_id FROM patients)
UNION ALL SELECT 'appointments → unknown doctor', COUNT(*) FROM appointments WHERE doctor_id NOT IN (SELECT doctor_id FROM doctors)
UNION ALL SELECT 'treatments → unknown appointment', COUNT(*) FROM treatments WHERE appointment_id NOT IN (SELECT appointment_id FROM appointments)
UNION ALL SELECT 'billing → unknown treatment', COUNT(*) FROM billing WHERE treatment_id NOT IN (SELECT treatment_id FROM treatments)
UNION ALL SELECT 'appointments with no bill', COUNT(*) FROM appointments WHERE appointment_id NOT IN (SELECT t.appointment_id FROM treatments t JOIN billing b ON b.treatment_id=t.treatment_id)""",
}

# One-click presets for the SQL Lab (run against the *unfiltered* data)
PRESETS = {
"Revenue collected vs pending (by month, with MoM %)": Q["monthly"].replace("{W}", "WHERE 1=1"),
"Doctor leaderboard (RANK window)": Q["doctor_scorecard"].replace("{W}", "WHERE 1=1"),
"Top 10 patients by lifetime billing": Q["patients360"].replace("{W}", "WHERE 1=1").replace("ORDER BY billed DESC", "ORDER BY billed DESC LIMIT 10"),
"Double-booked doctor slots": Q["double_booking"].replace("{W}", "WHERE 1=1"),
"Treatment profitability": Q["treatments"].replace("{W}", "WHERE 1=1"),
"Outstanding bills ageing": Q["aging"].replace("{W}", "WHERE 1=1"),
"Appointments by weekday & hour": Q["heatmap"].replace("{W}", "WHERE 1=1"),
"Data-quality checks": Q["dq_orphans"],
}


def where(f: dict, exclude=()):
    sql, p = ["WHERE 1=1"], []
    if f.get("date") and "date" not in exclude:
        sql.append("AND appointment_date BETWEEN ? AND ?"); p += list(f["date"])
    for field in ("branch", "specialization", "status", "payment_status"):
        vals = f.get(field)
        if vals and field not in exclude:
            sql.append(f"AND {field} IN ({','.join('?' * len(vals))})"); p += list(vals)
    return " ".join(sql), p


def q(name: str, f: dict, exclude=()) -> pd.DataFrame:
    w, p = where(f, exclude)
    sql = Q[name]
    return store.run(sql.replace("{W}", w), p * sql.count("{W}"))


def patient_timeline(pid: str) -> pd.DataFrame:
    return store.run("""
SELECT appointment_date, appointment_time, doctor_name, specialization, reason, status, treatment_type,
       amount, payment_status,
       SUM(amount) OVER (ORDER BY appointment_date, appointment_time) AS running_billed
FROM v_appt WHERE patient_id = ? ORDER BY appointment_date, appointment_time""", [pid])


def slot_conflict(doctor_id, date, time) -> int:
    r = store.run("SELECT COUNT(*) AS n FROM v_appt WHERE doctor_id=? AND appointment_date=? AND appointment_time=? AND status<>'Cancelled'",
                  [doctor_id, str(date), str(time)])
    return int(r.n[0])


def bounds():
    r = store.run("SELECT MIN(appointment_date) AS mn, MAX(appointment_date) AS mx FROM appointments")
    return r.mn[0], r.mx[0]


def forecast(m: pd.DataFrame, k=3):
    """Linear-trend forecast of collected revenue with a ±1σ band. Needs ≥3 months."""
    if len(m) < 3:
        return None
    y = m["collected"].to_numpy(float); x = np.arange(len(y))
    b, a = np.polyfit(x, y, 1)
    sd = float(np.std(y - (a + b * x), ddof=2))
    fx = np.arange(len(y), len(y) + k)
    yhat = np.maximum(a + b * fx, 0)
    months = pd.period_range(pd.Period(m["month"].iloc[-1], "M") + 1, periods=k, freq="M").astype(str)
    return pd.DataFrame({"month": months, "forecast": yhat, "low": np.maximum(yhat - sd, 0), "high": yhat + sd}), b


def insights(f: dict) -> list[tuple[str, str]]:
    """Auto-generated plain-language findings (computed from the SQL results)."""
    out = []
    k = q("kpis", f).iloc[0]
    if k.appts == 0:
        return out
    if k.billed:
        rate = 100 * k.collected / k.billed
        out.append(("💰", f"Only **{rate:.0f}%** of billed revenue is actually collected — **₹{k.pending + k.failed:,.0f}** is pending/failed."))
    leak = 100 * (k.cancelled + k.noshow) / k.appts
    out.append(("📉" if leak > 30 else "✅", f"**{leak:.0f}%** of appointments are cancelled or no-shows ({int(k.cancelled)} + {int(k.noshow)})."))
    ds = q("doctor_scorecard", f).fillna({"revenue_share_pct": 0, "leakage_pct": 0, "completion_pct": 0, "collected": 0})
    if len(ds) > 1:
        top, worst = ds.iloc[0], ds.sort_values("leakage_pct").iloc[-1]
        if top.collected > 0:
            out.append(("🏆", f"**{top.doctor_name}** ({top.specialization}) leads collections with ₹{top.collected:,.0f} ({top.revenue_share_pct:.0f}% share)."))
        else:
            out.append(("💡", "No bill is marked **Paid** yet, so doctor revenue is ₹0 — check the `payment_status` values in your billing file."))
        out.append(("⚠️", f"**{worst.doctor_name}** has the highest appointment leakage at {worst.leakage_pct:.0f}%."))
    m = q("monthly", f)
    if len(m) > 1:
        b = m.sort_values("collected").iloc[-1]
        out.append(("📈", f"Best collection month: **{b.month}** (₹{b.collected:,.0f})."))
    h = q("heatmap", f)
    if not h.empty:
        pk = h.groupby("hour").n.sum().idxmax()
        out.append(("🕒", f"Peak hour is **{int(pk):02d}:00** — schedule extra front-desk staff then."))
    n = len(q("double_booking", f))
    out.append(("🚨" if n else "✅", f"**{n}** double-booked doctor slot(s) detected." if n else "No double-booked doctor slots."))
    return out