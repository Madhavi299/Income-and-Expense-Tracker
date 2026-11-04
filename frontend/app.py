
import streamlit as st

from frontend.api_client import APIError, login, register


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

    st.caption(
        "Manage income, expenses, and bills in your own secure account."
    )

    login_tab, register_tab = st.tabs(
        ["Login", "Create account"]
    )

    # LOGIN
    with login_tab:

        with st.form("login_form"):

            email = st.text_input("Email")

            password = st.text_input(
                "Password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Login",
                use_container_width=True
            )

        if submitted:

            try:

                result = login(
                    email.strip(),
                    password
                )

                st.session_state.token = result["access_token"]

                st.session_state.user = result["user"]

                st.rerun()

            except APIError as exc:

                st.error(str(exc))

    # REGISTER
    with register_tab:

        with st.form("register_form"):

            username = st.text_input("Username")

            email = st.text_input("Email")

            password = st.text_input(
                "Password (at least 8 characters)",
                type="password"
            )

            confirm = st.text_input(
                "Confirm password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Create account",
                use_container_width=True
            )

        if submitted:

            if password != confirm:

                st.error("Passwords do not match.")

            else:

                try:

                    register(
                        username.strip(),
                        email.strip(),
                        password
                    )

                    st.success(
                        "Account created. Please log in."
                    )

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

    from frontend.pages.dashboard import page as dashboard_page

    from frontend.pages.add_transaction import page as add_page

    from frontend.pages.view_transactions import page as view_page

    from frontend.pages.manage_transactions import page as manage_page

    user = st.session_state.user or {}

    # SIDEBAR BRANDING
    with st.sidebar:

        st.title("💰 Expense Tracker")

        st.write(
            f"Logged in as **{user.get('username', 'User')}**"
        )

        st.divider()

        if st.button(
            "Log out",
            use_container_width=True
        ):

            logout()

    # TOP NAVIGATION + URL ROUTING
    pages = [

        st.Page(
            dashboard_page,
            title="Dashboard",
            url_path="dashboard",
            default=True
        ),

        st.Page(
            add_page,
            title="Add Transaction",
            url_path="add-transaction"
        ),

        st.Page(
            view_page,
            title="View Transactions",
            url_path="view-transactions"
        ),

        st.Page(
            manage_page,
            title="Manage Transactions",
            url_path="manage-transactions"
        ),

    ]

    navigation = st.navigation(
        pages,
        position="sidebar"
    )

    navigation.run()


# --------------------------------------------------
# APPLICATION START
# --------------------------------------------------

init_state()

if not st.session_state.token:

    auth_screen()

else:

    app_screen()
