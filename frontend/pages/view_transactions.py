import pandas as pd
import streamlit as st
from frontend.api_client import APIError, list_transactions

def page():
    st.title("📄 View Transactions")
    try:
        records = list_transactions(st.session_state.token)
    except APIError as exc:
        st.error(str(exc)); return
    if not records:
        st.info("No transactions found. Add one or upload a bill.")
        return
    df = pd.DataFrame(records)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.date
    search = st.text_input("Search title, category, or description")
    kind = st.selectbox("Transaction type", ["All", "Income", "Expense"])
    if search:
        mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        df = df[mask]
    if kind != "All":
        df = df[df["transaction_type"] == kind]
    st.dataframe(df.sort_values("transaction_date", ascending=False), use_container_width=True, hide_index=True)
    st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), "transactions.csv", "text/csv")
