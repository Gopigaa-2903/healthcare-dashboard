from datetime import date, time
from io import BytesIO

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import queries as Q
import store
from ui import (heat_scale, BLUE, GREEN, ORANGE, PALETTE, PINK, PURPLE, RED, STATUS_COLORS, TEAL, footer, inr, stat_cards,
                style_chart)

DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

# chart-key → (filter field, which axis carries the category)
XF_SOURCES = {"xf_status": ("status", "y"), "xf_pay": ("payment_status", "x"), "xf_spec": ("specialization", "y")}


# ───────────── shared helpers ─────────────
def F() -> dict:
    return st.session_state.get("F", {})


def nonce() -> int:
    return st.session_state.setdefault("xf_nonce", 0)


def sync_xf():
    """Read chart clicks (stored by Streamlit under each chart key) into cross-filters."""
    xf = {}
    for key, (field, axis) in XF_SOURCES.items():
        s = st.session_state.get(f"{key}_{nonce()}")
        try:
            pts = s["selection"]["points"] if s else []
        except (KeyError, TypeError):
            pts = []
        vals = [p.get(axis) for p in pts if p.get(axis) is not None]
        if vals:
            xf[field] = vals
    st.session_state["xf"] = xf


def clickable(fig, key, h=250):
    """Plot a chart whose bars act as filters for the whole dashboard."""
    st.plotly_chart(style_chart(fig, h), key=f"{key}_{nonce()}", on_select="rerun",
                    selection_mode="points", width="stretch")


def chip_bar():
    xf = st.session_state.get("xf", {})
    if not xf:
        st.caption("💡 Click any bar in *Status*, *Payment* or *Specialization* charts to filter the whole dashboard.")
        return
    c = st.columns([6, 1])
    c[0].markdown("".join(f'<span class="cc-chip">{k.replace("_", " ")}: {", ".join(map(str, v))}</span>' for k, v in xf.items()),
                  unsafe_allow_html=True)
    if c[1].button("✕ Clear", key="xf_clear", width="stretch"):
        st.session_state["xf_nonce"] = nonce() + 1
        st.session_state["xf"] = {}
        st.rerun()


def upload_box(mode="replace", key="up"):
    store.conn()
    n = st.session_state.setdefault("up_nonce", 0)
    files = st.file_uploader("Drop your files here — patients, doctors, appointments, treatments, billing (.csv / .xlsx)",
                             type=["csv", "xlsx", "xls"], accept_multiple_files=True, key=f"{key}_{n}")
    new = [f for f in files if f.file_id not in st.session_state["_seen"]]
    if new:
        log = []
        for f in new:
            log += store.ingest(f, mode)
            st.session_state["_seen"].add(f.file_id)
        st.session_state["_log"] = log
        st.rerun()
    for line in st.session_state["_log"]:
        st.markdown(line)


def empty_state():
    zero = lambda l, c, i: (l, "0", c, i, "waiting for data")
    stat_cards([zero("Appointments", BLUE, "📅"), zero("Patients", GREEN, "👥"), zero("Collected revenue", ORANGE, "₹"),
                zero("Outstanding", RED, "⏳"), zero("Completion rate", TEAL, "✅"), zero("Leakage rate", PINK, "📉")])
    st.markdown('<div class="cc-hero"><div class="ico">📥</div><h3>Upload your data to bring this dashboard to life</h3>'
                '<p>Everything starts at 0. Drop your CSV / Excel files below and every chart, KPI, ranking and forecast '
                'will be calculated from them instantly using SQL.</p></div>', unsafe_allow_html=True)
    with st.container(border=True):
        upload_box(key="up_home")
        if st.button("▶ Or load the built-in sample dataset", key="sample_home"):
            st.session_state["_log"] = store.load_sample()
            st.rerun()
    footer()


def report_bytes(f) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for sheet, name in [("KPIs", "kpis"), ("Monthly", "monthly"), ("Doctors", "doctor_scorecard"),
                            ("Treatments", "treatments"), ("Patients", "patients360"), ("Aging", "aging"),
                            ("Double bookings", "double_booking")]:
            Q.q(name, f).to_excel(xw, sheet_name=sheet, index=False)
    return buf.getvalue()


def _pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "0%"


# ───────────── Command Center ─────────────
def dashboard():
    st.title("Command Center")
    if not store.has_data():
        return empty_state()
    f = F()
    k = Q.q("kpis", f).iloc[0]
    top = st.columns([5, 1.3])
    with top[0]:
        chip_bar()
    top[1].download_button("⬇ Excel report", report_bytes(f), "citycare_report.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    if k.appts == 0:
        st.warning("No records match the current filters.")
        return

    daily = Q.q("daily", f)
    stat_cards([
        ("Appointments", f"{int(k.appts):,}", BLUE, "📅", f"{int(k.patients)} patients · {int(k.doctors)} doctors", daily["appts"]),
        ("Collected revenue", inr(k.collected), GREEN, "₹", f"of {inr(k.billed)} billed ({_pct(k.collected, k.billed)})", daily["collected"]),
        ("Outstanding", inr(k.pending + k.failed), RED, "⏳", f"pending {inr(k.pending)} · failed {inr(k.failed)}", None),
        ("Completed visits", f"{int(k.completed):,}", TEAL, "✅", f"{_pct(k.completed, k.appts)} completion rate", None),
        ("Cancelled + No-show", f"{int(k.cancelled + k.noshow):,}", PINK, "📉", f"{_pct(k.cancelled + k.noshow, k.appts)} leakage", None),
        ("Scheduled", f"{int(k.scheduled):,}", ORANGE, "🕒", "upcoming / open", None),
    ])
    st.write("")

    ins = Q.insights(f)
    c1, c2 = st.columns([1, 1.4])
    with c1, st.container(border=True):
        st.markdown("**🧠 Auto-insights**")
        for icon, text in ins:
            st.markdown(f'<div class="cc-insight"><span>{icon}</span><span>{text}</span></div>', unsafe_allow_html=True)
    with c2, st.container(border=True):
        st.markdown("**Monthly cash collection vs leakage**")
        m = Q.q("monthly", f)
        fig = go.Figure()
        for col, name, color in [("collected", "Paid", GREEN), ("pending", "Pending", ORANGE), ("failed", "Failed", RED)]:
            fig.add_bar(x=m["month"], y=m[col], name=name, marker_color=color)
        fig.update_layout(barmode="stack")
        fig.add_scatter(x=m["month"], y=m["mom_pct"], name="MoM % (collected)", yaxis="y2", mode="lines+markers",
                        line=dict(color="#151b2e", width=1.5, dash="dot"))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, ticksuffix="%"))
        st.plotly_chart(style_chart(fig, 330, legend=True), width="stretch")

    st.markdown("##### Click a bar to cross-filter everything")
    a, b, c = st.columns(3)
    with a, st.container(border=True):
        st.markdown("**Appointment status**")
        s = Q.q("status", f, exclude=("status",))
        clickable(px.bar(s, x="n", y="status", orientation="h", color="status", color_discrete_map=STATUS_COLORS), "xf_status")
    with b, st.container(border=True):
        st.markdown("**Bill payment status (₹)**")
        p = Q.q("payment_status", f, exclude=("payment_status",))
        clickable(px.bar(p, x="payment_status", y="amount", color="payment_status", color_discrete_map=STATUS_COLORS), "xf_pay")
    with c, st.container(border=True):
        st.markdown("**Specialization (appointments)**")
        sp = Q.q("specialization", f, exclude=("specialization",)).sort_values("appts")
        clickable(px.bar(sp, x="appts", y="specialization", orientation="h", color_discrete_sequence=[BLUE]), "xf_spec")

    d, e = st.columns(2)
    with d, st.container(border=True):
        st.markdown("**When are patients booked? (weekday × hour)**")
        h = Q.q("heatmap", f)
        if h.empty:
            st.caption("No time data.")
        else:
            pv = h.pivot_table(index="dow", columns="hour", values="n", fill_value=0).reindex(range(7), fill_value=0)
            pv.index = DOW
            fig = px.imshow(pv, aspect="auto", color_continuous_scale=heat_scale(), labels=dict(x="Hour", y="", color="Appts"))
            fig.update_xaxes(dtick=1)
            st.plotly_chart(style_chart(fig, 300).update_layout(coloraxis_showscale=False), width="stretch")
    with e, st.container(border=True):
        st.markdown("**Revenue flow: Specialization → Payment outcome**")
        fl = Q.q("flow", f)
        if fl.empty:
            st.caption("No billing data.")
        else:
            specs = sorted(fl.specialization.unique()); outs = ["Paid", "Pending", "Failed"]
            nodes = specs + [o for o in outs if o in set(fl.payment_status)]
            idx = {n: i for i, n in enumerate(nodes)}
            fl = fl[fl.payment_status.isin(nodes)]
            fig = go.Figure(go.Sankey(
                node=dict(label=nodes, pad=14, thickness=14,
                          color=[BLUE] * len(specs) + [STATUS_COLORS[n] for n in nodes[len(specs):]]),
                link=dict(source=[idx[s] for s in fl.specialization], target=[idx[o] for o in fl.payment_status],
                          value=fl.amount.tolist(), color=[STATUS_COLORS[o] + "55" for o in fl.payment_status])))
            st.plotly_chart(style_chart(fig, 300), width="stretch")
    footer()


# ───────────── Appointments ─────────────
def _next_id(table, prefix, col):
    n = store.run(f'SELECT COUNT(*) AS n FROM "{table}"').n[0] + 1
    while store.run(f'SELECT 1 FROM "{table}" WHERE {col}=?', [f"{prefix}{n:03d}"]).shape[0]:
        n += 1
    return f"{prefix}{n:03d}"


def appointments():
    st.title("Appointments")
    if not store.has_data():
        return empty_state()
    f = F()
    k = Q.q("kpis", f).iloc[0]
    stat_cards([("Total", f"{int(k.appts):,}", BLUE, "📅"), ("Scheduled", int(k.scheduled), GREEN, "🕒"),
                ("Completed", int(k.completed), TEAL, "✅"), ("Cancelled", int(k.cancelled), ORANGE, "❌"),
                ("No-show", int(k.noshow), RED, "🚫")])
    st.write("")
    dbk = Q.q("double_booking", f)
    if len(dbk):
        with st.container(border=True):
            st.markdown(f"**🚨 {len(dbk)} double-booked slot(s)** — same doctor, same date & time")
            st.dataframe(dbk, hide_index=True, width="stretch")

    with st.container(border=True):
        h = st.columns([3, 2])
        h[0].markdown("**All appointments (filtered)**")
        q = h[1].text_input("search", label_visibility="collapsed", placeholder="🔍 Search patient / doctor / status…")
        with st.expander("➕ Book appointment (checks doctor availability)"):
            pat = store.run("SELECT patient_id, first_name||' '||last_name AS n FROM patients ORDER BY 1")
            doc = store.run("SELECT doctor_id, 'Dr. '||first_name||' '||last_name AS n FROM doctors ORDER BY 1")
            with st.form("book", clear_on_submit=True):
                c = st.columns(3)
                pid = c[0].selectbox("Patient", pat.patient_id, format_func=lambda x: f"{x} · {pat.set_index('patient_id').n[x]}")
                did = c[1].selectbox("Doctor", doc.doctor_id, format_func=lambda x: f"{doc.set_index('doctor_id').n[x]}")
                dt = c[2].date_input("Date", date.today())
                tm = c[0].time_input("Time", time(10, 0)); status = c[1].selectbox("Status", ["Scheduled", "Completed", "Cancelled", "No-show"])
                reason = c[2].text_input("Reason")
                if st.form_submit_button("Book", type="primary"):
                    tstr = tm.strftime("%H:%M:%S")
                    if Q.slot_conflict(did, dt, tstr):
                        st.error("⚠️ That doctor already has an appointment at this date & time. Pick another slot.")
                    else:
                        con = store.conn()
                        con.execute("INSERT INTO appointments VALUES (?,?,?,?,?,?,?)",
                                    (_next_id("appointments", "A", "appointment_id"), pid, did, str(dt), tstr, reason, status))
                        con.commit()
                        st.success("Appointment booked.")
        w, p = Q.where(f)
        df = Q.q("appt_list", f)
        if q:
            df = df[df.astype(str).agg(" ".join, axis=1).str.lower().str.contains(q.lower(), regex=False)]
        st.dataframe(df, hide_index=True, width="stretch",
                     column_config={"Amount": st.column_config.NumberColumn(format="₹%.0f")})
        st.caption(f"{len(df):,} rows")
    footer()


# ───────────── Doctors ─────────────
def doctors():
    st.title("Doctor Scorecards")
    if not store.has_data():
        return empty_state()
    f = F()
    ds = Q.q("doctor_scorecard", f)
    if ds.empty:
        st.warning("No records match the current filters."); return
    stat_cards([("Doctors active", len(ds), BLUE, "🩺"), ("Avg completion", f"{ds.completion_pct.mean():.0f}%", GREEN, "✅"),
                ("Avg leakage", f"{ds.leakage_pct.mean():.0f}%", RED, "📉"),
                ("Top earner", ds.iloc[0].doctor_name, ORANGE, "🏆", inr(ds.iloc[0].collected))])
    st.write("")
    a, b = st.columns(2)
    with a, st.container(border=True):
        st.markdown("**Collected revenue by doctor**")
        fig = px.bar(ds.sort_values("collected"), x="collected", y="doctor_name", orientation="h", color="specialization",
                     color_discrete_sequence=PALETTE)
        st.plotly_chart(style_chart(fig, 340, legend=True), width="stretch")
    with b, st.container(border=True):
        st.markdown("**Experience vs revenue per appointment** (bubble = workload)")
        fig = px.scatter(ds, x="experience", y="revenue_per_appt", size="appts", color="specialization",
                         hover_name="doctor_name", color_discrete_sequence=PALETTE)
        st.plotly_chart(style_chart(fig, 340, legend=True), width="stretch")
    with st.container(border=True):
        st.markdown("**Leaderboard** (SQL: CTE + RANK() window)")
        view = ds[["revenue_rank", "doctor_name", "specialization", "branch", "experience", "appts", "patients",
                   "completion_pct", "leakage_pct", "collected", "outstanding", "revenue_share_pct"]]
        st.dataframe(view, hide_index=True, width="stretch", column_config={
            "revenue_rank": "Rank", "doctor_name": "Doctor", "specialization": "Specialization", "branch": "Branch",
            "experience": st.column_config.NumberColumn("Exp (yrs)", format="%d"), "appts": "Appts", "patients": "Patients",
            "completion_pct": st.column_config.ProgressColumn("Completion %", min_value=0, max_value=100, format="%.0f%%"),
            "leakage_pct": st.column_config.ProgressColumn("Leakage %", min_value=0, max_value=100, format="%.0f%%"),
            "collected": st.column_config.NumberColumn("Collected", format="₹%.0f"),
            "outstanding": st.column_config.NumberColumn("Outstanding", format="₹%.0f"),
            "revenue_share_pct": st.column_config.NumberColumn("Share %", format="%.1f%%")})
    footer()


# ───────────── Patient 360 ─────────────
def patients():
    st.title("Patient 360")
    if not store.has_data():
        return empty_state()
    f = F()
    pl = Q.q("patients360", f)
    if pl.empty:
        st.warning("No records match the current filters."); return
    stat_cards([("Patients", len(pl), BLUE, "👥"), ("Avg visits / patient", f"{pl.visits.mean():.1f}", GREEN, "🔁"),
                ("Insured", f"{(pl.insurance_provider != 'Self-pay').sum()} / {len(pl)}", TEAL, "🛡️"),
                ("Outstanding", inr(pl.outstanding.sum()), RED, "⏳")])
    st.write("")
    pick = st.selectbox("Select a patient", pl.patient_id, format_func=lambda x: f"{pl.set_index('patient_id').patient_name[x]}  ({x})")
    r = pl.set_index("patient_id").loc[pick]
    stat_cards([("Patient", r.patient_name, BLUE, "🙂", f"{r.gender} · {int(r.age) if pd.notna(r.age) else '—'} yrs · {r.insurance_provider}"),
                ("Visits", int(r.visits), GREEN, "📅", f"{int(r.completed)} completed"),
                ("Lifetime billed", inr(r.billed), ORANGE, "₹", f"rank #{int(r.value_rank)} of {len(pl)}"),
                ("Paid", inr(r.paid), TEAL, "✅"), ("Outstanding", inr(r.outstanding), RED, "⏳")])
    st.write("")
    tl = Q.patient_timeline(pick)
    a, b = st.columns([1.2, 1])
    with a, st.container(border=True):
        st.markdown("**Visit timeline** (running total via SQL window)")
        st.dataframe(tl, hide_index=True, width="stretch", column_config={
            "amount": st.column_config.NumberColumn("Amount", format="₹%.0f"),
            "running_billed": st.column_config.NumberColumn("Running billed", format="₹%.0f")})
    with b, st.container(border=True):
        st.markdown("**Cumulative billing**")
        fig = px.line(tl, x="appointment_date", y="running_billed", markers=True, color_discrete_sequence=[BLUE])
        st.plotly_chart(style_chart(fig, 300), width="stretch")
    with st.container(border=True):
        st.markdown("**Top patients by lifetime billing**")
        st.dataframe(pl.head(15)[["value_rank", "patient_id", "patient_name", "visits", "billed", "paid", "outstanding", "last_visit"]],
                     hide_index=True, width="stretch", column_config={
                         "billed": st.column_config.NumberColumn(format="₹%.0f"), "paid": st.column_config.NumberColumn(format="₹%.0f"),
                         "outstanding": st.column_config.NumberColumn(format="₹%.0f")})
    footer()


# ───────────── Revenue ─────────────
def revenue():
    st.title("Revenue")
    if not store.has_data():
        return empty_state()
    f = F()
    k = Q.q("kpis", f).iloc[0]
    if k.appts == 0:
        st.warning("No records match the current filters."); return
    stat_cards([("Billed", inr(k.billed), BLUE, "🧾"), ("Collected (Paid only)", inr(k.collected), GREEN, "✅", _pct(k.collected, k.billed) + " of billed"),
                ("Pending", inr(k.pending), ORANGE, "🕒"), ("Failed", inr(k.failed), RED, "❌"),
                ("Avg bill", inr(k.billed / k.appts), TEAL, "₹")])
    st.write("")
    m = Q.q("monthly", f)
    a, b = st.columns([1.6, 1])
    with a, st.container(border=True):
        st.markdown("**Collected revenue & 3-month forecast** (linear trend, ±1σ band)")
        fig = go.Figure()
        fig.add_scatter(x=m["month"], y=m["collected"], name="Collected", mode="lines+markers", line=dict(color=GREEN, width=3))
        fc = Q.forecast(m)
        if fc:
            fdf, slope = fc
            fig.add_scatter(x=list(fdf.month) + list(fdf.month[::-1]), y=list(fdf.high) + list(fdf.low[::-1]), fill="toself",
                            fillcolor="rgba(63,120,240,.15)", line=dict(width=0), name="±1σ band", hoverinfo="skip")
            fig.add_scatter(x=fdf.month, y=fdf.forecast, name="Forecast", mode="lines+markers", line=dict(color=BLUE, dash="dash", width=3))
        st.plotly_chart(style_chart(fig, 330, legend=True), width="stretch")
        if fc:
            st.caption(f"Trend: {'+' if slope >= 0 else '−'}{inr(abs(slope))} per month · next 3 months ≈ {inr(fdf.forecast.sum())}")
        else:
            st.caption("Forecast needs at least 3 months of data.")
    with b, st.container(border=True):
        st.markdown("**Billed vs collected by payment method**")
        pm = Q.q("payment_method", f)
        fig = go.Figure([go.Bar(x=pm.method, y=pm.billed, name="Billed", marker_color="#b8c0cc"),
                         go.Bar(x=pm.method, y=pm.collected, name="Collected", marker_color=GREEN)])
        fig.update_layout(barmode="group")
        st.plotly_chart(style_chart(fig, 330, legend=True), width="stretch")

    c, d = st.columns(2)
    with c, st.container(border=True):
        st.markdown("**Treatment profitability** (collection % is the leak to fix)")
        tr = Q.q("treatments", f)
        st.dataframe(tr, hide_index=True, width="stretch", column_config={
            "treatment_type": "Treatment", "cases": "Cases", "avg_cost": st.column_config.NumberColumn("Avg cost", format="₹%.0f"),
            "billed": st.column_config.NumberColumn("Billed", format="₹%.0f"),
            "collected": st.column_config.NumberColumn("Collected", format="₹%.0f"),
            "collection_pct": st.column_config.ProgressColumn("Collection %", min_value=0, max_value=100, format="%.0f%%"),
            "rev_rank": "Rank"})
    with d, st.container(border=True):
        st.markdown("**Outstanding bills ageing**")
        ag = Q.q("aging", f)
        if ag.empty:
            st.caption("Nothing outstanding 🎉")
        else:
            order = ["0-30 days", "31-90 days", "91-180 days", "180+ days"]
            fig = px.bar(ag, x="bucket", y="amount", color="payment_status", color_discrete_map=STATUS_COLORS,
                         category_orders={"bucket": order})
            st.plotly_chart(style_chart(fig, 260, legend=True), width="stretch")
    e, g = st.columns(2)
    with e, st.container(border=True):
        st.markdown("**Collected revenue by age group**")
        ag = Q.q("age_group", f)
        st.plotly_chart(style_chart(px.bar(ag, x="age_group", y="collected", color_discrete_sequence=[TEAL]), 250), width="stretch")
    with g, st.container(border=True):
        st.markdown("**Visit reasons & leakage %**")
        rs = Q.q("reasons", f)
        st.dataframe(rs, hide_index=True, width="stretch", column_config={
            "reason": "Reason", "n": "Visits", "leakage_pct": st.column_config.ProgressColumn("Cancel/No-show %", min_value=0, max_value=100, format="%.0f%%")})
    footer()


# ───────────── SQL Lab ─────────────
def sql_lab():
    st.title("SQL Lab")
    st.caption("Every number in this app is a SQL query. Run the originals or write your own (read-only).")
    if not store.has_data():
        return empty_state()
    name = st.selectbox("Query library", ["— write my own —"] + list(Q.PRESETS))
    default = Q.PRESETS.get(name, "SELECT doctor_name, COUNT(*) AS appts\nFROM v_appt\nGROUP BY doctor_name\nORDER BY appts DESC;")
    sql = st.text_area("SQL", default.strip(), height=240, key=f"sql_{name}")
    with st.expander("Tables & columns available"):
        st.markdown("`v_appt` (joined view): " + ", ".join(store.run("PRAGMA table_info(v_appt)").name))
        for t, c in store.SCHEMA.items():
            st.markdown(f"`{t}`: {', '.join(c)}")
    if st.button("▶ Run query", type="primary"):
        s = sql.strip().rstrip(";")
        if not s.lower().startswith(("select", "with", "pragma table_info")) or ";" in s:
            st.error("Only a single read-only SELECT / WITH query is allowed.")
        else:
            try:
                df = store.run(s)
            except Exception as e:  # noqa: BLE001
                st.error(f"SQL error: {e}"); return
            st.success(f"{len(df)} rows × {len(df.columns)} columns")
            st.dataframe(df, hide_index=True, width="stretch")
            num = df.select_dtypes("number").columns.tolist()
            cat = [c for c in df.columns if c not in num]
            if num and cat and 1 < len(df) <= 60:
                st.plotly_chart(style_chart(px.bar(df, x=cat[0], y=num[0], color_discrete_sequence=[BLUE]), 300), width="stretch")
            st.download_button("⬇ Download CSV", df.to_csv(index=False), "query_result.csv", "text/csv")
    footer()


# ───────────── Data Hub ─────────────
def data_hub():
    st.title("Data Hub")
    st.caption("Upload files → data loads into SQL tables → every page updates. Excel files with several sheets are auto-split.")
    store.conn()
    with st.container(border=True):
        mode = st.radio("When a table already has data", ["replace", "merge"], horizontal=True,
                        format_func=lambda x: "Replace it" if x == "replace" else "Merge (add new IDs, update existing)")
        upload_box(mode, key="up_hub")
        c = st.columns([1, 1, 3])
        if c[0].button("▶ Load sample data"):
            st.session_state["_log"] = store.load_sample(); st.rerun()
        if c[1].button("🗑 Clear all data"):
            store.clear_all(); st.session_state["up_nonce"] = st.session_state.get("up_nonce", 0) + 1
            st.session_state["xf_nonce"] = nonce() + 1; st.rerun()
    cnt = store.counts()
    stat_cards([(t.title(), f"{n:,}", col, ic) for (t, n), col, ic in
                zip(cnt.items(), [GREEN, BLUE, PURPLE, TEAL, ORANGE], ["👥", "🩺", "📅", "💊", "🧾"])])
    st.write("")
    a, b = st.columns(2)
    with a, st.container(border=True):
        st.markdown("**Data-quality checks** (SQL joins)")
        if store.has_data():
            dq = store.run(Q.Q["dq_orphans"])
            dq["status"] = dq["rows"].map(lambda x: "✅ OK" if x == 0 else "⚠️ Check")
            st.dataframe(dq, hide_index=True, width="stretch")
        else:
            st.caption("Load data to run checks.")
    with b, st.container(border=True):
        st.markdown("**Expected columns / templates**")
        for t, cols in store.SCHEMA.items():
            st.download_button(f"⬇ {t}.csv template", ",".join(cols) + "\n", f"{t}_template.csv", "text/csv", key=f"tpl_{t}")
    if store.has_data():
        with st.container(border=True):
            t = st.selectbox("Preview table", list(store.SCHEMA))
            st.dataframe(store.run(f'SELECT * FROM "{t}" LIMIT 200'), hide_index=True, width="stretch")
    footer()