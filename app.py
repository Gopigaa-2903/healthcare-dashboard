from datetime import date, timedelta

import streamlit as st

import login
import pages as pg
import queries as Q
import store
from ui import inject_css, theme_toggle

PRESET_DAYS = {"30D": 30, "90D": 90, "6M": 182, "1Y": 365}

st.set_page_config(page_title="CityCare Analytics", page_icon="➕", layout="wide")
inject_css()

# ── login gate ──
if not st.session_state.get("auth"):
    st.markdown("<style>[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl']{display:none}</style>",
                unsafe_allow_html=True)
    st.navigation([st.Page(login.login_page, title="Sign in", url_path="login")], position="hidden").run()
    st.stop()

store.conn()  # empty in-memory SQL database for this session (everything starts at 0)

nav = st.navigation([
    st.Page(pg.dashboard, title="Command Center", icon="📊", url_path="dashboard", default=True),
    st.Page(pg.appointments, title="Appointments", icon="📅", url_path="appointments"),
    st.Page(pg.doctors, title="Doctor Scorecards", icon="👨‍⚕️", url_path="doctors"),
    st.Page(pg.patients, title="Patient 360", icon="👥", url_path="patients"),
    st.Page(pg.revenue, title="Revenue", icon="💰", url_path="revenue"),
    st.Page(pg.sql_lab, title="SQL Lab", icon="🧮", url_path="sql-lab"),
    st.Page(pg.data_hub, title="Data Hub", icon="☁️", url_path="data-hub"),
])

with st.sidebar:
    st.markdown('<div class="cc-brand"><div class="cc-logo">+</div><div><b>CityCare</b><small>Analytics</small></div></div>',
                unsafe_allow_html=True)
    st.caption(f"👤 {st.session_state.get('user_name') or st.session_state.get('user', '')}")
    theme_toggle("dark_side")
    st.markdown('<div class="cc-section">🎛️ FILTERS · apply to every page</div>', unsafe_allow_html=True)
    f = {}
    if store.has_data():
        ver = store.version()
        tag = f"{ver}_{st.session_state.setdefault('flt_n', 0)}"
        mn, mx = Q.bounds()
        lo, hi = date.fromisoformat(mn), date.fromisoformat(mx)

        preset = st.segmented_control("Period", ["All", "30D", "90D", "6M", "1Y", "Custom"], default="All",
                                      key=f"pre{tag}", label_visibility="collapsed") or "All"
        start, end = lo, hi
        if preset == "Custom":
            dr = st.date_input("Custom range", (lo, hi), min_value=lo, max_value=hi, key=f"dr{tag}")
            if isinstance(dr, (tuple, list)) and len(dr) == 2:
                start, end = dr
        elif preset != "All":
            start = max(lo, hi - timedelta(days=PRESET_DAYS[preset]))
        st.markdown(f'<div class="cc-range">📅 {start:%d %b %Y} → {end:%d %b %Y}</div>', unsafe_allow_html=True)
        if (start, end) != (lo, hi):
            f["date"] = (start.isoformat(), end.isoformat())

        branches = store.run("SELECT DISTINCT branch FROM v_appt ORDER BY 1").branch.tolist()
        specs = store.run("SELECT DISTINCT specialization FROM v_appt ORDER BY 1").specialization.tolist()
        f["branch"] = st.multiselect("🏥 Hospital branch", branches, key=f"br{tag}", placeholder="All branches")
        sidebar_spec = st.multiselect("🩺 Specialization", specs, key=f"sp{tag}", placeholder="All specializations")
        pg.sync_xf()
        xf = st.session_state.get("xf", {})
        f["specialization"] = xf.get("specialization") or sidebar_spec
        for k in ("status", "payment_status"):
            if xf.get(k):
                f[k] = xf[k]

        shown, total = int(Q.q("kpis", f).appts[0]), int(Q.q("kpis", {}).appts[0])
        active = sum(bool(v) for v in f.values())
        st.markdown(f'<div class="cc-summary">Showing <b>{shown:,}</b> of {total:,} appointments'
                    f'<br>{active} filter{"s" if active != 1 else ""} active</div>', unsafe_allow_html=True)
        if st.button("↺ Reset filters", width="stretch", disabled=not active and preset == "All"):
            st.session_state["flt_n"] += 1
            st.session_state["xf_nonce"] = st.session_state.get("xf_nonce", 0) + 1
            st.session_state["xf"] = {}
            st.rerun()
    else:
        st.caption("Filters appear once data is loaded.")
        st.session_state["xf"] = {}
    st.session_state["F"] = f

    c = store.counts()
    rows, tables = sum(c.values()), sum(v > 0 for v in c.values())
    st.markdown(f'<span class="cc-badge {"" if rows else "off"}"><i></i>{rows:,} rows · {tables}/5 tables loaded</span>',
                unsafe_allow_html=True)
    st.write("")
    if st.button("Sign out", width="stretch"):
        dark = st.session_state.get("_dark", False)
        st.session_state.clear()
        st.session_state["_dark"] = dark
        st.rerun()

nav.run()