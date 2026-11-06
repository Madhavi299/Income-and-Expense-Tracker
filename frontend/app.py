
import sys
from pathlib import Path

import streamlit as st

repository_root = str(Path(__file__).resolve().parent.parent)
if repository_root not in sys.path:
    sys.path.insert(0, repository_root)

from frontend.api_client import APIError, login, register
from frontend.theme import render_theme_control


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Personal Income & Expense Tracker",
    page_icon="💰",
    layout="wide",
)


# --------------------------------------------------
# INITIALIZE SESSION
# --------------------------------------------------

def init_state():
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("auth_mode", "Login")


# --------------------------------------------------
# LOGIN AND REGISTER PAGE
# --------------------------------------------------

def auth_screen():
    st.title("💰 Personal Income & Expense Tracker")
    _, content, _ = st.columns([1, 1.5, 1])
    with content:
        st.subheader("Welcome")
        login_tab, register_tab = st.tabs(["Login", "Create account"])

        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button(
                    "Login", use_container_width=True
                )

            if submitted:
                try:
                    result = login(email.strip(), password)
                    st.session_state.token = result["access_token"]
                    st.session_state.user = result["user"]
                    st.rerun()
                except APIError as exc:
                    st.error(str(exc))

        with register_tab:
            with st.form("register_form"):
                username = st.text_input("Username", placeholder="Your name")
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input(
                    "Password (at least 8 characters)", type="password"
                )
                confirm = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button(
                    "Create account", use_container_width=True
                )

            if submitted:
                if password != confirm:
                    st.error("Passwords do not match.")
                else:
                    try:
                        register(username.strip(), email.strip(), password)
                        st.success("Account created. Please log in.")
                    except APIError as exc:
                        st.error(str(exc))


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

def logout():

    st.session_state.token = None

    st.session_state.user = None

    st.rerun()


# --------------------------------------------------
# AUTHENTICATED APPLICATION
# --------------------------------------------------

def app_screen():

    user = st.session_state.user or {}

    if user.get("role") == "admin":
        from frontend.pages.admin import page as admin_page
        pages = [
            st.Page(
                admin_page,
                title="Admin Console",
                url_path="admin",
                default=True,
                icon="🛡️",
            )
        ]
    else:
        from frontend.pages.dashboard import page as dashboard_page
        from frontend.pages.add_transaction import page as add_page
        from frontend.pages.view_transactions import page as view_page
        from frontend.pages.manage_transactions import page as manage_page
        pages = [
            st.Page(
                dashboard_page,
                title="Dashboard",
                url_path="dashboard",
                default=True,
                icon="📊",
            ),
            st.Page(
                add_page,
                title="Add Transaction",
                url_path="add-transaction",
                icon="➕",
            ),
            st.Page(
                view_page,
                title="View Transactions",
                url_path="view-transactions",
                icon="🧾",
            ),
            st.Page(
                manage_page,
                title="Manage Transactions",
                url_path="manage-transactions",
                icon="⚙️",
            ),
        ]

    # SIDEBAR BRANDING
    with st.sidebar:

        st.markdown("## 💸 Moneywise")
        st.caption("PERSONAL FINANCE")
        st.divider()
        st.markdown(f"**{user.get('username', 'User')}**")
        st.caption(f"Logged in as {user.get('username', 'User')}")
        st.caption("Administrator" if user.get("role") == "admin" else "Personal account")

        if st.button(
            "Sign out",
            use_container_width=True,
        ):
            logout()

    navigation = st.navigation(
        pages,
        position="sidebar"
    )

    navigation.run()


# --------------------------------------------------
# APPLICATION START
# --------------------------------------------------

init_state()
render_theme_control()

if not st.session_state.token:
    navigation = st.navigation(
        [st.Page(auth_screen, title="Login", default=True)],
        position="hidden",
    )
    navigation.run()

else:

    app_screen()
