import pandas as pd
import streamlit as st
from frontend.api_client import APIError, list_transactions

def page():
    st.title("📊 Dashboard")
    try:
        records = list_transactions(st.session_state.token)
    except APIError as exc:
        st.error(str(exc)); return
    if not records:
        st.info("No transactions yet. Add a transaction or upload a bill to get started.")
        return
    df = pd.DataFrame(records)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    income = df.loc[df.transaction_type == "Income", "amount"].sum()
    expenses = df.loc[df.transaction_type == "Expense", "amount"].sum()
    balance = income - expenses
    savings_rate = (balance / income * 100) if income else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Income", f"₹{income:,.2f}")
    c2.metric("Total Expenses", f"₹{expenses:,.2f}")
    c3.metric("Balance", f"₹{balance:,.2f}")
    c4.metric("Savings Rate", f"{savings_rate:.1f}%")
    st.subheader("Monthly cash flow")
    df["month"] = df.transaction_date.dt.to_period("M").astype(str)
    monthly = df.pivot_table(index="month", columns="transaction_type", values="amount", aggfunc="sum", fill_value=0)
    st.bar_chart(monthly)
    st.subheader("Expenses by category")
    expenses_df = df[df.transaction_type == "Expense"].groupby("category")["amount"].sum()
    if not expenses_df.empty:
        st.plotly_chart if False else None
        st.bar_chart(expenses_df)
    st.subheader("Recent transactions")
    st.dataframe(df.sort_values("transaction_date", ascending=False), use_container_width=True, hide_index=True)
