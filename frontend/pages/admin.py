import pandas as pd
import streamlit as st

from frontend.api_client import (
    APIError,
    list_activity,
    list_admin_users,
    update_admin_user,
)


def _users_tab(token, current_user):
    page_number = st.session_state.setdefault("admin_user_page", 1)
    previous, next_page = st.columns(2)
    if previous.button("Previous users", disabled=page_number <= 1):
        st.session_state.admin_user_page -= 1
        st.rerun()

    try:
        users = list_admin_users(token, limit=100, offset=(page_number - 1) * 100)
    except APIError as exc:
        st.error(str(exc))
        return

    if next_page.button("Next users", disabled=len(users) < 100):
        st.session_state.admin_user_page += 1
        st.rerun()

    st.caption(f"Page {page_number}")
    if not users:
        st.info("No user accounts found on this page.")
        return

    st.dataframe(
        [
            {
                "ID": user["id"],
                "Username": user["username"],
                "Email": user["email"],
                "Role": user["role"],
                "Active": user["is_active"],
                "Total Income": f'₹{user["total_income"]:,.2f}',
                "Total Expenses": f'₹{user["total_expenses"]:,.2f}',
                "Balance": f'₹{user["balance"]:,.2f}',
                "Created": user["created_at"],
            }
            for user in users
        ],
        use_container_width=True,
        hide_index=True,
    )

    choices = {
        f'#{user["id"]} — {user["username"]} ({user["email"]})': user
        for user in users
    }
    selected = st.selectbox("Select an account to manage", list(choices))
    user = choices[selected]
    is_self = user["id"] == current_user["id"]
    with st.form("admin_user_update"):
        role = st.selectbox(
            "Role",
            ["user", "admin"],
            index=0 if user["role"] == "user" else 1,
            disabled=is_self,
        )
        is_active = st.checkbox(
            "Account is active",
            value=user["is_active"],
            disabled=is_self,
        )
        submitted = st.form_submit_button(
            "Save account changes",
            disabled=is_self,
            use_container_width=True,
        )

    if is_self:
        st.info("For safety, you cannot change your own role or active status.")
    if submitted:
        changes = {}
        if role != user["role"]:
            changes["role"] = role
        if is_active != user["is_active"]:
            changes["is_active"] = is_active
        if not changes:
            st.info("No changes to save.")
            return
        try:
            update_admin_user(token, user["id"], changes)
            st.success("User account updated.")
            st.rerun()
        except APIError as exc:
            st.error(str(exc))


def _activity_tab(token):
    try:
        events = list_activity(token, limit=200)
    except APIError as exc:
        st.error(str(exc))
        return
    if not events:
        st.info("No application activity has been recorded yet.")
        return
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Time": event["created_at"],
                    "Actor": event["actor_username"] or "System/unknown",
                    "Action": event["action"],
                    "Target": event["target_username"] or "",
                    "Details": event["details"] or "",
                }
                for event in events
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )


def page():
    st.title("Administrator Console")
    st.caption("Manage accounts, roles, activation, and application activity.")
    current_user = st.session_state.user or {}
    accounts_tab, activity_tab = st.tabs(["User accounts", "Application activity"])
    with accounts_tab:
        _users_tab(st.session_state.token, current_user)
    with activity_tab:
        _activity_tab(st.session_state.token)
