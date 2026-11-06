import pandas as pd
import streamlit as st

from frontend.api_client import (
    APIError,
    delete_transaction,
    list_transactions,
    update_transaction,
)

CATEGORIES = [
    "Food",
    "Groceries",
    "Transport",
    "Utilities",
    "Healthcare",
    "Shopping",
    "Education",
    "Salary",
    "Other",
]


def page():
    st.title("🛠️ Manage Transactions")
    st.caption("Find a record, review it, and make changes with confidence.")
    try:
        records = list_transactions(st.session_state.token)
    except APIError as exc:
        st.error(str(exc))
        return
    if not records:
        st.info("No transactions to manage yet. Add one to get started.")
        return

    with st.container(border=True):
        st.markdown("#### Find a transaction")
        filters = st.columns([1.5, 1, 1.5])
        search = filters[0].text_input(
            "Search records", placeholder="Search by title or category"
        )
        kind_filter = filters[1].selectbox(
            "Transaction type", ["All", "Expense", "Income"]
        )
        sort_order = filters[2].selectbox(
            "Order", ["Newest first", "Oldest first", "Largest amount"]
        )

    filtered_records = [
        record
        for record in records
        if (kind_filter == "All" or record["transaction_type"] == kind_filter)
        and (
            not search.strip()
            or search.casefold() in record["title"].casefold()
            or search.casefold() in record["category"].casefold()
            or search.casefold() in (record.get("description") or "").casefold()
        )
    ]
    if sort_order == "Oldest first":
        filtered_records.sort(key=lambda record: record["transaction_date"])
    elif sort_order == "Largest amount":
        filtered_records.sort(key=lambda record: record["amount"], reverse=True)
    else:
        filtered_records.sort(key=lambda record: record["transaction_date"], reverse=True)
    st.caption(f"{len(filtered_records)} matching records")
    if not filtered_records:
        st.info("No transactions match those filters. Try another search or type.")
        return

    choices = {
        f'{record["transaction_date"]} · {record["title"]} · ₹{record["amount"]:,.2f}': record
        for record in filtered_records
    }
    selected_label = st.selectbox("Select a transaction", list(choices))
    record = choices[selected_label]
    with st.container(border=True):
        st.caption(f'SELECTED RECORD · {record["transaction_type"].upper()}')
        summary_title, summary_amount, summary_category, summary_date = st.columns(
            [2, 1, 1, 1]
        )
        summary_title.markdown(f'### {record["title"]}')
        summary_amount.metric("Amount", f'₹{record["amount"]:,.2f}')
        summary_category.metric("Category", record["category"])
        summary_date.metric("Date", record["transaction_date"])

    with st.container(border=True):
        st.markdown("#### ✏️ Update transaction")
        st.caption("Changes update your dashboard and totals immediately.")
        with st.form("edit_transaction_form"):
            title = st.text_input("Title", value=record["title"])
            columns = st.columns(2)
            amount = columns[0].number_input(
                "Amount (₹)",
                min_value=0.01,
                value=float(record["amount"]),
                step=100.0,
                format="%.2f",
            )
            kind = columns[1].selectbox(
                "Transaction type",
                ["Income", "Expense"],
                index=0 if record["transaction_type"] == "Income" else 1,
            )
            category_index = (
                CATEGORIES.index(record["category"])
                if record["category"] in CATEGORIES
                else CATEGORIES.index("Other")
            )
            category = st.selectbox("Category", CATEGORIES, index=category_index)
            tx_date = st.date_input(
                "Transaction date",
                value=pd.to_datetime(record["transaction_date"]).date(),
            )
            description = st.text_area(
                "Note", value=record.get("description") or ""
            )
            save = st.form_submit_button(
                "Save Transaction", use_container_width=True
            )
        if save:
            if not title.strip():
                st.error("Please enter a title.")
            else:
                try:
                    update_transaction(
                        st.session_state.token,
                        record["id"],
                        {
                            "title": title.strip(),
                            "amount": amount,
                            "transaction_type": kind,
                            "category": category,
                            "transaction_date": tx_date.isoformat(),
                            "description": description,
                        },
                    )
                    st.success("Transaction updated.")
                    st.toast("Your changes have been saved.", icon="✅")
                    st.rerun()
                except APIError as exc:
                    st.error(str(exc))

    with st.container(border=True):
        st.markdown("#### 🗑️ Remove this transaction")
        st.warning(
            "Deleting a transaction is permanent and will update your totals."
        )
        confirm = st.checkbox(
            "I confirm I want to delete this transaction.",
            key=f"confirm_delete_{record['id']}",
        )
        if st.button(
            "Delete Transaction",
            type="primary",
            disabled=not confirm,
            use_container_width=True,
        ):
            try:
                delete_transaction(st.session_state.token, record["id"])
                st.success("Transaction deleted.")
                st.rerun()
            except APIError as exc:
                st.error(str(exc))
