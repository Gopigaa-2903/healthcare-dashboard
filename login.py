import time

import streamlit as st

import auth
from ui import theme_toggle


def _enter(email, name):
    st.session_state["auth"] = True
    st.session_state["user"] = email.strip().lower()
    st.session_state["user_name"] = name
    st.rerun()


def _hero():
    st.markdown("""
<div class="lg-hero">
  <div class="lg-blob lg-b1"></div><div class="lg-blob lg-b2"></div><div class="lg-blob lg-b3"></div>
  <div style="display:flex;gap:12px;align-items:center;position:relative">
    <div class="cc-logo" style="background:rgba(255,255,255,.22);box-shadow:none">+</div>
    <div><b style="font-size:20px">CityCare</b><br><small style="opacity:.85">Hospital Analytics</small></div>
  </div>
  <h1>Care with precision.<br>Manage with clarity.</h1>
  <p>Upload your hospital data and watch revenue, doctor performance and patient flow come alive — powered by live SQL.</p>
  <div class="lg-pulse"><svg viewBox="0 0 260 50"><path d="M0 25 H60 L72 5 L88 45 L102 15 L112 25 H170 L182 8 L196 42 L208 25 H260"/></svg></div>
  <div style="position:relative;margin-top:10px">
    <span class="lg-chip">📈 Live KPIs</span><span class="lg-chip">🧮 SQL Lab</span>
    <span class="lg-chip">🔮 Revenue forecast</span><span class="lg-chip">👤 Patient 360</span>
  </div>
</div>""", unsafe_allow_html=True)


def _sign_in_tab():
    with st.form("signin"):
        email = st.text_input("Email address", placeholder="you@hospital.com")
        pw = st.text_input("Password", type="password", placeholder="••••••••")
        if st.form_submit_button("Sign in →", type="primary", width="stretch"):
            ok, res = auth.authenticate(email, pw)
            if ok:
                _enter(email, res)
            st.error(res)
    if st.button("Forgot password?", key="to_forgot", type="tertiary"):
        st.session_state["auth_view"] = "forgot"
        st.rerun()


def _sign_up_tab():
    with st.form("signup"):
        name = st.text_input("Full name")
        email = st.text_input("Email address", key="su_email", placeholder="you@hospital.com")
        c = st.columns(2)
        pw = c[0].text_input("Password", type="password", key="su_pw", help="Min 8 characters, letters + numbers")
        pw2 = c[1].text_input("Confirm password", type="password", key="su_pw2")
        if st.form_submit_button("Create account", type="primary", width="stretch"):
            ok, res = auth.register(name, email, pw, pw2)
            if ok:
                _enter(email, res)
            st.error(res)


def _forgot_view():
    st.markdown("<p class='lg-title'>Reset password 🔑</p>", unsafe_allow_html=True)
    if not st.session_state.get("fp_sent"):
        st.caption("Enter your account email — we'll send a 6-digit code.")
        with st.form("fp1"):
            email = st.text_input("Email address")
            if st.form_submit_button("Send code", type="primary", width="stretch"):
                code = auth.create_reset_code(email) if auth.EMAIL_RE.match(email.strip()) else None
                err = None
                if code:
                    if auth.email_configured():
                        ok, err = auth.send_code_email(email.strip(), code)
                        if not ok:
                            st.error(err); st.stop()
                    elif auth.dev_mode():
                        st.session_state["fp_dev_code"] = code      # testing only
                    else:
                        st.error("Email is not set up yet. " + auth.diagnose()); st.stop()
                st.session_state.update(fp_sent=True, fp_email=email.strip().lower(), fp_time=time.time())
                st.rerun()
    else:
        email = st.session_state["fp_email"]
        st.success(f"If **{email}** is registered, a code has been sent. It is valid for 10 minutes.")
        if st.session_state.get("fp_dev_code"):
            st.warning(f"DEV MODE — code: **{st.session_state['fp_dev_code']}**")
        with st.form("fp2"):
            code = st.text_input("6-digit code", max_chars=6)
            pw = st.text_input("New password", type="password")
            pw2 = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Reset password", type="primary", width="stretch"):
                ok, msg = auth.reset_password(email, code, pw, pw2)
                if ok:
                    for k in ("fp_sent", "fp_email", "fp_dev_code", "fp_time"):
                        st.session_state.pop(k, None)
                    st.session_state["auth_view"] = "main"
                    st.session_state["flash"] = msg
                    st.rerun()
                st.error(msg)
        wait = 60 - int(time.time() - st.session_state.get("fp_time", 0))
        if st.button(f"Resend code{f' ({wait}s)' if wait > 0 else ''}", disabled=wait > 0, key="fp_resend"):
            for k in ("fp_sent", "fp_dev_code"):
                st.session_state.pop(k, None)
            st.rerun()
    if st.button("← Back to sign in", key="fp_back", type="tertiary"):
        for k in ("fp_sent", "fp_email", "fp_dev_code", "fp_time"):
            st.session_state.pop(k, None)
        st.session_state["auth_view"] = "main"
        st.rerun()


def login_page():
    _, tg = st.columns([5, 1])
    with tg:
        theme_toggle("dark_login")
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        _hero()
    with right:
        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            if st.session_state.get("auth_view") == "forgot":
                _forgot_view()
            else:
                st.markdown("<p class='lg-title'>Welcome 👋</p>", unsafe_allow_html=True)
                st.caption("Sign in, or create an account to open your analytics workspace.")
                if msg := st.session_state.pop("flash", None):
                    st.success(msg)
                t1, t2 = st.tabs(["Sign in", "Sign up"])
                with t1:
                    _sign_in_tab()
                with t2:
                    _sign_up_tab()