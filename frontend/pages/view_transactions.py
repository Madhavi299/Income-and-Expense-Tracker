import pandas as pd
import streamlit as st
from datetime import date, timedelta
from frontend.api_client import APIError, list_transactions

def page():
    st.title("📄 View Transactions")
    st.caption("Explore your activity, narrow it down, and export exactly what you need.")
    try:
        records = list_transactions(st.session_state.token)
    except APIError as exc:
        st.error(str(exc)); return
    if not records:
        st.info("No transactions found. Add one or upload a bill.")
        return
    df = pd.DataFrame(records)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.date

    with st.container(border=True):
        st.markdown("#### Find transactions")
        filter_columns = st.columns([1.5, 1, 1, 1])
        search = filter_columns[0].text_input(
            "Search title, category, or description",
            placeholder="Title, category, or description",
        )
        period = filter_columns[1].selectbox(
            "Date range", ["All time", "Today", "Last 7 days", "This month"]
        )
        kinds = filter_columns[1].multiselect(
            "Type",
            ["Income", "Expense"],
            default=["Income", "Expense"],
            key="view_transaction_types",
        )
        categories = sorted(df["category"].dropna().unique().tolist())
        selected_categories = filter_columns[2].multiselect(
            "Category", categories, default=categories
        )
        sort_order = filter_columns[3].selectbox(
            "Sort by", ["Newest first", "Oldest first", "Largest amount"]
        )

        date_columns = st.columns([1, 1, 2])
        earliest = min(df["transaction_date"])
        latest = max(df["transaction_date"])
        today = date.today()
        if period == "Today":
            start_date = end_date = today
        elif period == "Last 7 days":
            start_date, end_date = today - timedelta(days=6), today
        elif period == "This month":
            start_date, end_date = today.replace(day=1), today
        else:
            start_date, end_date = earliest, latest
        with date_columns[0]:
            custom_dates = st.checkbox("Choose dates", key="view_custom_dates")
        if custom_dates:
            with date_columns[1]:
                start_date = st.date_input(
                    "From",
                    value=min(max(earliest, start_date), latest),
                    min_value=earliest,
                    max_value=latest, key="view_start_date",
                )
            with date_columns[2]:
                end_date = st.date_input(
                    "To",
                    value=min(max(earliest, end_date), latest),
                    min_value=earliest,
                    max_value=latest, key="view_end_date",
                )
        else:
            date_columns[1].caption(f"From **{start_date:%b %d, %Y}**")
            date_columns[2].caption(f"Through **{end_date:%b %d, %Y}**")

    filtered = df.loc[
        df["transaction_type"].isin(kinds)
        & df["category"].isin(selected_categories)
        & df["transaction_date"].between(start_date, end_date)
    ].copy()
    if search.strip():
        search_mask = filtered.astype(str).apply(
            lambda column: column.str.contains(search.strip(), case=False, na=False)
        )
        filtered = filtered.loc[search_mask.any(axis=1)]

    income_total = filtered.loc[
        filtered["transaction_type"] == "Income", "amount"
    ].sum()
    expense_total = filtered.loc[
        filtered["transaction_type"] == "Expense", "amount"
    ].sum()
    summary_income, summary_expenses, summary_balance, summary_count = st.columns(4)
    summary_income.metric("Income", f"₹{income_total:,.2f}")
    summary_expenses.metric("Expenses", f"₹{expense_total:,.2f}")
    summary_balance.metric("Net balance", f"₹{income_total - expense_total:,.2f}")
    summary_count.metric("Matching records", len(filtered))
    if filtered.empty:
        st.info("No transactions match these filters. Adjust your search or date range.")
        return

    if sort_order == "Oldest first":
        ordered = filtered.sort_values("transaction_date", ascending=True)
    elif sort_order == "Largest amount":
        ordered = filtered.sort_values("amount", ascending=False)
    else:
        ordered = filtered.sort_values("transaction_date", ascending=False)

    st.markdown("#### Matching activity")
    st.caption("Select any column header to sort the table.")
    with st.container(border=True):
        st.dataframe(ordered, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️  Download filtered transactions",
            ordered.to_csv(index=False).encode("utf-8"),
            "transactions.csv",
            "text/csv",
            use_container_width=True,
        )
