import pandas as pd
import streamlit as st
from frontend.api_client import APIError, list_transactions, update_transaction, delete_transaction

def page():
    st.title("🛠️ Manage Transactions")
    try:
        records = list_transactions(st.session_state.token)
    except APIError as exc:
        st.error(str(exc)); return
    if not records:
        st.info("No transactions available to manage.")
        return
    choices = {f'#{r["id"]} — {r["title"]} — ₹{r["amount"]:.2f}': r for r in records}
    selected_label = st.selectbox("Select a transaction", list(choices))
    record = choices[selected_label]
    st.subheader("Edit transaction")
    with st.form("edit_transaction_form"):
        title = st.text_input("Title", value=record["title"])
        amount = st.number_input("Amount (₹)", min_value=0.01, value=float(record["amount"]), step=10.0)
        kind = st.selectbox("Transaction type", ["Income", "Expense"], index=0 if record["transaction_type"] == "Income" else 1)
        categories = ["Food", "Groceries", "Transport", "Utilities", "Healthcare", "Shopping", "Education", "Salary", "Other"]
        category = st.selectbox("Category", categories, index=categories.index(record["category"]) if record["category"] in categories else categories.index("Other"))
        tx_date = st.date_input("Transaction date", value=pd.to_datetime(record["transaction_date"]).date())
        description = st.text_area("Description", value=record.get("description") or "")
        save = st.form_submit_button("Save Transaction", use_container_width=True)
    if save:
        try:
            update_transaction(st.session_state.token, record["id"], {"title": title.strip(), "amount": amount, "transaction_type": kind, "category": category, "transaction_date": tx_date.isoformat(), "description": description})
            st.success("Transaction updated.")
            st.rerun()
        except APIError as exc:
            st.error(str(exc))
    st.divider()
    st.subheader("Delete transaction")
    confirm = st.checkbox("I confirm I want to delete this transaction.")
    if st.button("Delete Transaction", type="secondary", disabled=not confirm):
        try:
            delete_transaction(st.session_state.token, record["id"])
            st.success("Transaction deleted.")
            st.rerun()
        except APIError as exc:
            st.error(str(exc))
