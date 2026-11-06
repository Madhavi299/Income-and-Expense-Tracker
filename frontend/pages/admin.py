import pandas as pd
import streamlit as st

from frontend.api_client import (
    APIError,
    list_activity,
    list_admin_users,
    update_admin_user,
)


def _users_tab(token, current_user):
    st.markdown("#### Account directory")
    st.caption("Review account status and select a user to view their financial summary.")
    page_number = st.session_state.setdefault("admin_user_page", 1)
    previous, page_label, next_page = st.columns([1, 2, 1])
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

    page_label.markdown(f"<div style='text-align:center;padding-top:0.5rem'>Page {page_number}</div>", unsafe_allow_html=True)
    if not users:
        st.info("No user accounts found on this page.")
        return

    filters = st.columns([2, 1])
    search = filters[0].text_input(
        "Search this page", placeholder="Username or email", key="admin_user_search"
    )
    role_filter = filters[1].selectbox(
        "Role", ["All", "user", "admin"], key="admin_user_role_filter"
    )
    shown_users = [
        user
        for user in users
        if (role_filter == "All" or user["role"] == role_filter)
        and (
            not search.strip()
            or search.casefold() in user["username"].casefold()
            or search.casefold() in user["email"].casefold()
        )
    ]
    active_count = sum(user["is_active"] for user in shown_users)
    total_users, active_users, admin_users = st.columns(3)
    total_users.metric("Accounts shown", len(shown_users))
    active_users.metric("Active", active_count)
    admin_users.metric("Administrators", sum(user["role"] == "admin" for user in shown_users))
    if not shown_users:
        st.info("No accounts match these filters.")
        return

    with st.container(border=True):
        st.dataframe(
            [
                {
                    "ID": user["id"],
                    "Username": user["username"],
                    "Email": user["email"],
                    "Role": user["role"].title(),
                    "Status": "Active" if user["is_active"] else "Inactive",
                    "Created": pd.to_datetime(user["created_at"]).strftime("%b %d, %Y"),
                }
                for user in shown_users
            ],
            use_container_width=True,
            hide_index=True,
        )

    choices = {
        f'#{user["id"]} — {user["username"]} ({user["email"]})': user
        for user in shown_users
    }
    selected = st.selectbox("Select an account to manage", list(choices))
    user = choices[selected]
    st.markdown(f"#### Financial snapshot · {user['username']}")
    st.caption("Aggregate totals only; individual transaction records are not shown here.")
    income, expenses, balance = st.columns(3)
    income.metric("Total income", f'₹{user["total_income"]:,.2f}')
    expenses.metric("Total expenses", f'₹{user["total_expenses"]:,.2f}')
    balance.metric("Net balance", f'₹{user["balance"]:,.2f}')

    is_self = user["id"] == current_user["id"]
    with st.container(border=True):
        st.markdown("#### Account permissions")
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
    st.markdown("#### Recent activity")
    st.caption("A record of account and security events.")
    try:
        events = list_activity(token, limit=200)
    except APIError as exc:
        st.error(str(exc))
        return
    if not events:
        st.info("No application activity has been recorded yet.")
        return
    with st.container(border=True):
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
    st.title("Administrator console")
    st.caption("Manage access, monitor account health, and review application activity.")
    current_user = st.session_state.user or {}
    accounts_tab, activity_tab = st.tabs(["👥 Accounts", "🕘 Activity"])
    with accounts_tab:
        _users_tab(st.session_state.token, current_user)
    with activity_tab:
        _activity_tab(st.session_state.token)
