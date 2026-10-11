import streamlit as st

BLUE, GREEN, PURPLE, ORANGE, TEAL, PINK, RED = (
    "#3f78f0", "#22b07d", "#8b5cf6", "#f5a524", "#14b8c4", "#ec4899", "#e5484d")
PALETTE = [BLUE, GREEN, TEAL, PURPLE, PINK, "#b8c0cc"]
STATUS_COLORS = {"Completed": GREEN, "Scheduled": BLUE, "Cancelled": ORANGE, "No-show": RED, "Paid": GREEN,
                 "Pending": ORANGE, "Failed": RED, "No bill": "#b8c0cc"}

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family:'Poppins', sans-serif; }

/* ── lively gradient background ── */
.stApp {
  background: var(--app-bg); background-attachment: fixed;
}
[data-testid="stHeader"] { background:transparent; }
.block-container { padding-top:1.2rem; max-width:1400px; }

/* ── sidebar ── */
[data-testid="stSidebar"] { background:var(--side-bg); border-right:1px solid var(--line); }
[data-testid="stSidebarNav"] a { border-radius:10px; margin:2px 0; transition:all .2s ease; }
[data-testid="stSidebarNav"] a:hover { background:#3f78f01a; transform:translateX(3px); }
[data-testid="stSidebarNav"] a[aria-current="page"] { background:linear-gradient(90deg,#3f78f0,#8b5cf6) !important; box-shadow:0 6px 16px rgba(63,120,240,.35); }
[data-testid="stSidebarNav"] a[aria-current="page"] * { color:#fff !important; }

/* ── headings ── */
h1 { font-size:1.9rem !important; font-weight:800 !important; letter-spacing:-.5px;
     background:var(--h1-grad); -webkit-background-clip:text; background-clip:text;
     -webkit-text-fill-color:transparent; }
h5, h3 { font-weight:700 !important; }

/* ── glass cards ── */
.cc-card, [data-testid="stVerticalBlockBorderWrapper"] {
  background:var(--card-bg) !important; backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
  border:1px solid var(--card-border) !important; border-radius:18px !important;
  box-shadow:var(--shadow);
}
.cc-card { padding:14px 16px 10px; height:100%; transition:transform .25s ease, box-shadow .25s ease; position:relative; overflow:hidden; }
.cc-card:hover { transform:translateY(-4px); box-shadow:0 16px 36px rgba(63,120,240,.22); }
.cc-card::after { content:""; position:absolute; left:0; top:0; height:4px; width:100%; background:linear-gradient(90deg,#3f78f0,#8b5cf6,#ec4899); opacity:.85; }
.cc-brand { display:flex; align-items:center; gap:12px; padding:6px 4px 10px; }
.cc-logo { height:42px; width:42px; border-radius:13px; background:linear-gradient(135deg,#3f78f0,#8b5cf6); color:#fff;
  display:grid; place-items:center; font-size:22px; font-weight:800; box-shadow:0 8px 18px rgba(63,120,240,.4); }
.cc-brand b { font-size:18px; color:var(--text); } .cc-brand small { display:block; color:var(--muted); }
.cc-stat-top { display:flex; align-items:center; gap:10px; }
.cc-stat-ico { height:38px; width:38px; border-radius:12px; display:grid; place-items:center; font-size:18px; }
.cc-stat-label { font-size:12px; color:var(--muted); } .cc-stat-val { font-size:23px; font-weight:700; color:var(--text); line-height:1.15; }
.cc-sub { font-size:11px; color:var(--muted); margin-top:2px; min-height:15px; }
.cc-spark { display:flex; align-items:flex-end; gap:2px; height:26px; margin-top:6px; }
.cc-spark i { flex:1; border-radius:2px 2px 0 0; opacity:.85; min-height:2px; }
.cc-insight { display:flex; gap:10px; padding:9px 12px; background:var(--insight-bg); border-radius:12px; margin-bottom:7px; font-size:13.5px;
  transition:transform .2s ease; border-left:3px solid #3f78f0; }
.cc-insight:hover { transform:translateX(4px); }
.cc-chip { display:inline-block; background:linear-gradient(90deg,#3f78f0,#8b5cf6); color:#fff; padding:3px 12px; border-radius:99px; font-size:12px; font-weight:600; margin-right:6px; }
.cc-hero { text-align:center; padding:30px 10px 8px; }
.cc-hero .ico { height:80px; width:80px; border-radius:24px; background:linear-gradient(135deg,#3f78f033,#8b5cf633); display:inline-grid; place-items:center; font-size:40px;
  animation:cc-float 3.5s ease-in-out infinite; }
.cc-hero p { color:var(--muted); max-width:520px; margin:6px auto 0; }
.cc-footer { margin-top:30px; padding-top:10px; border-top:1px solid var(--line); font-size:12px; color:var(--muted); }

/* ── buttons ── */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  border-radius:12px; font-weight:600; transition:all .2s ease; }
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] {
  background:linear-gradient(90deg,#3f78f0,#8b5cf6); border:none; box-shadow:0 8px 18px rgba(63,120,240,.35); }
.stButton > button:hover, .stDownloadButton > button:hover { transform:translateY(-2px); box-shadow:0 8px 18px rgba(63,120,240,.25); }

/* ── login page ── */
.lg-hero { position:relative; overflow:hidden; border-radius:26px; padding:48px 42px; min-height:560px; color:#fff;
  background:linear-gradient(135deg,#2748c9,#5b6cf0,#8b5cf6,#14b8c4); background-size:300% 300%; animation:cc-grad 12s ease infinite;
  box-shadow:0 24px 60px rgba(63,120,240,.40); }
.lg-hero h1 { color:#fff !important; -webkit-text-fill-color:#fff !important; background:none !important; font-size:2.5rem !important; margin-top:70px; line-height:1.15; }
.lg-hero p { opacity:.9; max-width:400px; }
.lg-chip { display:inline-block; background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.3); backdrop-filter:blur(6px);
  border-radius:14px; padding:10px 14px; font-size:13px; margin:6px 8px 0 0; }
.lg-blob { position:absolute; border-radius:50%; background:rgba(255,255,255,.14); animation:cc-float 7s ease-in-out infinite; }
.lg-b1 { width:220px; height:220px; right:-60px; top:-60px; }
.lg-b2 { width:140px; height:140px; right:60px; bottom:50px; animation-delay:1.5s; }
.lg-b3 { width:90px; height:90px; left:40%; bottom:-30px; animation-delay:3s; }
.lg-pulse { display:inline-block; margin-top:26px; }
.lg-pulse svg { width:260px; height:50px; }
.lg-pulse path { stroke:#fff; stroke-width:3; fill:none; stroke-dasharray:420; stroke-dashoffset:420; animation:cc-ecg 2.6s linear infinite; }
.lg-title { font-size:2rem; font-weight:800; color:var(--text); margin:0; }

.cc-section { font-size:11px; font-weight:700; letter-spacing:1.4px; color:var(--muted); margin:14px 0 6px; }
.cc-badge { display:inline-flex; align-items:center; gap:8px; padding:6px 12px; border-radius:99px; font-size:12px; font-weight:600;
  background:rgba(34,176,125,.14); color:#22b07d; }
.cc-badge i { height:8px; width:8px; border-radius:50%; background:#22b07d; box-shadow:0 0 0 0 rgba(34,176,125,.6); animation:cc-pulse 1.8s infinite; }
.cc-badge.off { background:rgba(150,160,190,.16); color:var(--muted); } .cc-badge.off i { background:#9aa5c6; animation:none; }
.cc-summary { margin:10px 0 4px; padding:10px 12px; border-radius:12px; font-size:12.5px; background:var(--insight-bg); border-left:3px solid #3f78f0; color:var(--text); }
.cc-range { font-size:11.5px; color:var(--muted); margin:-4px 0 6px; }
@keyframes cc-pulse { 0%{box-shadow:0 0 0 0 rgba(34,176,125,.55)} 70%{box-shadow:0 0 0 8px rgba(34,176,125,0)} 100%{box-shadow:0 0 0 0 rgba(34,176,125,0)} }
@keyframes cc-grad { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
@keyframes cc-float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-14px)} }
@keyframes cc-ecg { to { stroke-dashoffset:0; } }
.cc-logo, .cc-chip { color:#fff !important; }
.lg-hero, .lg-hero * { color:#fff !important; }
</style>
"""

THEMES = {
    "light": dict(
        app_bg="radial-gradient(circle at 8% 12%, rgba(63,120,240,.20), transparent 38%), radial-gradient(circle at 92% 18%, rgba(139,92,246,.18), transparent 40%), radial-gradient(circle at 75% 92%, rgba(20,184,196,.18), transparent 42%), radial-gradient(circle at 15% 88%, rgba(236,72,153,.10), transparent 40%), linear-gradient(135deg,#f3f7ff 0%,#faf5ff 55%,#effcf8 100%)",
        side_bg="linear-gradient(180deg,#ffffff 0%,#eef3ff 100%)", card_bg="rgba(255,255,255,.72)",
        card_border="rgba(255,255,255,.9)", text="#151b2e", muted="#6b7385", line="#e1e8f7",
        insight_bg="rgba(63,120,240,.07)", h1_grad="linear-gradient(90deg,#1f3fa8,#8b5cf6 60%,#ec4899)", shadow="0 8px 28px rgba(31,63,168,.08), 0 1px 2px rgba(16,23,43,.05)"),
    "dark": dict(
        app_bg="radial-gradient(circle at 8% 12%, rgba(63,120,240,.22), transparent 38%), radial-gradient(circle at 92% 18%, rgba(139,92,246,.20), transparent 40%), radial-gradient(circle at 75% 92%, rgba(20,184,196,.14), transparent 42%), radial-gradient(circle at 15% 88%, rgba(236,72,153,.10), transparent 40%), linear-gradient(135deg,#0a0f1f 0%,#111a33 55%,#0b1822 100%)",
        side_bg="linear-gradient(180deg,#0f1630 0%,#0a0f22 100%)", card_bg="rgba(24,32,58,.72)",
        card_border="rgba(120,140,200,.20)", text="#e8ecf8", muted="#9aa5c6", line="#243055",
        insight_bg="rgba(63,120,240,.16)", h1_grad="linear-gradient(90deg,#9db8ff,#c9b2ff 60%,#ff9bd0)", shadow="0 8px 28px rgba(0,0,0,.35), 0 1px 2px rgba(0,0,0,.3)"),
}

DARK_CSS = """
<style>
/* text */
.stApp, .stApp p, .stApp li, .stApp label, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
[data-testid="stWidgetLabel"] *, [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li,
[data-testid="stSidebar"] *, [data-testid="stToolbar"] *, [data-testid="stExpander"] summary *,
[data-testid="stRadio"] *, [data-testid="stCheckbox"] *, [data-testid="stToggle"] *, .stTabs [data-baseweb="tab"] * { color:#e8ecf8; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *, small { color:#b4bee0 !important; opacity:1 !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] * { color:#fff !important; }
.stApp h1 { opacity:1; }

/* input widgets: native light widget → inverted to dark (works whatever Streamlit's inner markup is) */
[data-testid="stDateInput"], [data-testid="stSelectbox"], [data-testid="stMultiSelect"], [data-testid="stTextInput"],
[data-testid="stTextArea"], [data-testid="stNumberInput"], [data-testid="stTimeInput"] { filter:invert(.9) hue-rotate(180deg); }
[data-testid="stDateInput"] *, [data-testid="stSelectbox"] *, [data-testid="stMultiSelect"] *, [data-testid="stTextInput"] *,
[data-testid="stTextArea"] *, [data-testid="stNumberInput"] *, [data-testid="stTimeInput"] * {
  color:#262730 !important; -webkit-text-fill-color:#262730 !important; }
/* drop-down lists & calendar pop-ups (rendered outside the widget) */
[data-baseweb="popover"] { filter:invert(.9) hue-rotate(180deg); }
[data-baseweb="popover"] * { color:#262730 !important; -webkit-text-fill-color:#262730 !important; }

/* buttons (incl. file-uploader "Upload" button) */
.stButton > button:not([kind="primary"]):not([kind="tertiary"]), .stDownloadButton > button, [data-testid="stFileUploader"] button,
button[kind="secondary"], [data-testid^="stBaseButton-secondary"] {
  background:#1a2342 !important; color:#e8ecf8 !important; border:1px solid #33417a !important; }
.stButton > button:not([kind="primary"]):not([kind="tertiary"]) *, .stDownloadButton > button *, [data-testid="stFileUploader"] button * { color:#e8ecf8 !important; }
button[kind="primary"] *, button[kind="primaryFormSubmit"] * { color:#fff !important; }

/* segmented control (period buttons) & pills */
[data-testid="stSegmentedControl"] button, [data-testid="stPills"] button,
[data-testid^="stBaseButton-segmented_control"], [data-testid^="stBaseButton-pills"] {
  background:#1a2342 !important; color:#e8ecf8 !important; border:1px solid #33417a !important; }
[data-testid="stSegmentedControl"] button *, [data-testid="stPills"] button * { color:#e8ecf8 !important; -webkit-text-fill-color:#e8ecf8 !important; }
[data-testid="stBaseButton-segmented_controlActive"], [data-testid="stBaseButton-pillsActive"],
[data-testid="stSegmentedControl"] button[aria-checked="true"], [data-testid="stSegmentedControl"] button[aria-pressed="true"],
[data-testid="stPills"] button[aria-checked="true"], [data-testid="stPills"] button[aria-pressed="true"] {
  background:linear-gradient(90deg,#3f78f0,#8b5cf6) !important; border-color:transparent !important; }
[data-testid="stBaseButton-segmented_controlActive"] *, [data-testid="stBaseButton-pillsActive"] *,
[data-testid="stSegmentedControl"] button[aria-checked="true"] *, [data-testid="stSegmentedControl"] button[aria-pressed="true"] * { color:#fff !important; -webkit-text-fill-color:#fff !important; }
/* text-style (tertiary) buttons like "Forgot password?" stay transparent */
[data-testid="stBaseButton-tertiary"], button[kind="tertiary"] { background:transparent !important; border:none !important; }
[data-testid="stBaseButton-tertiary"] *, button[kind="tertiary"] * { color:#9db8ff !important; }

/* uploader, expander, tabs, alerts, tooltips */
[data-testid="stFileUploaderDropzone"] { background:#1a2342 !important; border:1px dashed #44528f !important; }
[data-testid="stFileUploaderDropzone"] * { color:#b4bee0 !important; }
[data-testid="stExpander"] details { background:rgba(24,32,58,.6) !important; border-color:#243055 !important; }
.stTabs [data-baseweb="tab-list"] { border-bottom:1px solid #243055; }
[data-testid="stTooltipContent"], [data-baseweb="tooltip"] * { background:#26335f !important; color:#e8ecf8 !important; }
[data-testid="stDataFrame"] { filter:invert(1) hue-rotate(180deg); border-radius:12px; }
</style>
"""


def is_dark() -> bool:
    return bool(st.session_state.get("_dark", False))


def theme_toggle(key="dark_ui"):
    """Light / Dark switch. The callback runs *before* the rerun, so the new theme shows immediately."""
    st.toggle("🌙 Dark mode", value=is_dark(), key=key,
              on_change=lambda: st.session_state.update(_dark=st.session_state[key]))


def heat_scale():
    return ["#16213f", BLUE] if is_dark() else ["#eef3ff", BLUE]


def inject_css():
    t = THEMES["dark" if is_dark() else "light"]
    vars_css = "<style>:root{" + "".join(f"--{k.replace('_', '-')}:{v};" for k, v in t.items()) + "}</style>"
    st.markdown(vars_css + BASE_CSS + (DARK_CSS if is_dark() else ""), unsafe_allow_html=True)


def _spark(vals, color):
    vals = [float(v) for v in vals][-28:]
    if len(vals) < 2:
        return '<div class="cc-spark"></div>'
    mx = max(vals) or 1
    bars = "".join(f'<i style="height:{max(v / mx * 100, 6):.0f}%;background:{color}"></i>' for v in vals)
    return f'<div class="cc-spark">{bars}</div>'


def stat_cards(items, per_row=None):
    """items: (label, value, color, icon[, subtitle[, sparkline values]])"""
    cols = st.columns(per_row or len(items))
    for i, it in enumerate(items):
        label, value, color, icon = it[:4]
        sub = it[4] if len(it) > 4 else ""
        spark = _spark(it[5], color) if len(it) > 5 and it[5] is not None else ""
        with cols[i % len(cols)]:
            st.markdown(
                f'<div class="cc-card"><div class="cc-stat-top"><div class="cc-stat-ico" style="background:{color}22;color:{color}">{icon}</div>'
                f'<div><div class="cc-stat-label">{label}</div><div class="cc-stat-val">{value}</div></div></div>'
                f'<div class="cc-sub">{sub}</div>{spark}</div>', unsafe_allow_html=True)


def footer():
    st.markdown('<div class="cc-footer">© CityCare Hospital Analytics · all figures computed live with SQL from the data you uploaded</div>',
                unsafe_allow_html=True)


def inr(x):
    x = float(x or 0)
    if abs(x) >= 1e7: return f"₹{x / 1e7:.2f} Cr"
    if abs(x) >= 1e5: return f"₹{x / 1e5:.2f} L"
    return f"₹{x:,.0f}"


def style_chart(fig, h=280, legend=False):
    fg = "#e8ecf8" if is_dark() else "#151b2e"
    fig.update_layout(height=h, margin=dict(l=0, r=10, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", showlegend=legend, font=dict(size=11, family="Poppins, sans-serif", color=fg),
                      legend=dict(orientation="h", y=-0.18))
    fig.update_xaxes(showgrid=False, linecolor="rgba(0,0,0,0)")
    fig.update_yaxes(gridcolor="rgba(150,165,210,.18)" if is_dark() else "rgba(120,140,190,.18)", zeroline=False)
    return fig