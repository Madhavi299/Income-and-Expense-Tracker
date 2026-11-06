import pandas as pd
import streamlit as st
from frontend.api_client import APIError, list_transactions

def page():
    st.title("📄 View Transactions")
    st.caption("Search, filter, and export your income and expenses.")
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
        filter_columns = st.columns([1.5, 1, 1])
        search = filter_columns[0].text_input(
            "Search title, category, or description",
            placeholder="Title, category, or description",
        )
        kinds = filter_columns[1].multiselect(
            "Type", ["Income", "Expense"], default=["Income", "Expense"]
        )
        categories = sorted(df["category"].dropna().unique().tolist())
        selected_categories = filter_columns[2].multiselect(
            "Category", categories, default=categories
        )

        date_columns = st.columns([1, 1, 2])
        earliest = min(df["transaction_date"])
        latest = max(df["transaction_date"])
        start_date = date_columns[0].date_input(
            "From", value=earliest, min_value=earliest, max_value=latest
        )
        end_date = date_columns[1].date_input(
            "To", value=latest, min_value=earliest, max_value=latest
        )
        date_columns[2].caption(
            f"{len(df)} transactions · {len(categories)} categories"
        )

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

    total = filtered["amount"].sum()
    st.caption(f"{len(filtered)} matching transactions · Total amount ₹{total:,.2f}")
    if filtered.empty:
        st.info("No transactions match these filters. Adjust your search or date range.")
        return

    ordered = filtered.sort_values("transaction_date", ascending=False)
    st.dataframe(ordered, use_container_width=True, hide_index=True)
    st.download_button(
        "Download filtered transactions",
        ordered.to_csv(index=False).encode("utf-8"),
        "transactions.csv",
        "text/csv",
    )
