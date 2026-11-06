from datetime import date, timedelta

import altair as alt
import pandas as pd
import streamlit as st
from frontend.api_client import APIError, list_transactions


def _period_bounds(period: str, today: date) -> tuple[date, date]:
    if period == "Daily":
        return today, today
    if period == "Weekly":
        return today - timedelta(days=6), today
    if period == "Monthly":
        return today.replace(day=1), today
    raise ValueError(f"Unsupported dashboard period: {period}")


def page():
    st.title("📊 Dashboard")
    st.caption("A live view of your income, spending, and cash flow.")
    try:
        records = list_transactions(st.session_state.token)
    except APIError as exc:
        st.error(str(exc))
        return
    if not records:
        st.info("Your dashboard is ready. Add a transaction to see your insights.")
        return

    df = pd.DataFrame(records)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    filter_columns = st.columns([1.2, 1, 1.5])
    period = filter_columns[0].radio(
        "Time period", ["Daily", "Weekly", "Monthly"], index=2, horizontal=True
    )
    kinds = ["All", "Income", "Expense"]
    kind = filter_columns[1].selectbox("Transaction type", kinds)
    search = filter_columns[2].text_input(
        "Quick search", placeholder="Search title, category, or note"
    )

    today = date.today()
    start_date, end_date = _period_bounds(period, today)
    period_df = df.loc[
        df["transaction_date"].dt.date.between(start_date, end_date)
    ].copy()
    if kind != "All":
        period_df = period_df.loc[period_df["transaction_type"] == kind]
    if search.strip():
        search_match = period_df.astype(str).apply(
            lambda column: column.str.contains(search.strip(), case=False, na=False)
        )
        period_df = period_df.loc[search_match.any(axis=1)]

    income = period_df.loc[
        period_df.transaction_type == "Income", "amount"
    ].sum()
    expenses = period_df.loc[
        period_df.transaction_type == "Expense", "amount"
    ].sum()
    balance = income - expenses
    savings_rate = (balance / income * 100) if income else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Income", f"₹{income:,.2f}")
    c2.metric("Total Expenses", f"₹{expenses:,.2f}")
    c3.metric("Balance", f"₹{balance:,.2f}")
    c4.metric("Savings Rate", f"{savings_rate:.1f}%")
    st.caption(
        f"Showing {len(period_df)} transactions · "
        f"{start_date:%b %d, %Y} – {end_date:%b %d, %Y}"
    )

    if period_df.empty:
        st.info("No transactions match these filters. Try another period or search.")
        return

    chart_text = "#e6edf3" if st.session_state.get("dark_mode") else "#1f2937"
    chart_colors = [
        "#4f46e5",
        "#06b6d4",
        "#f97316",
        "#ec4899",
        "#14b8a6",
        "#eab308",
        "#8b5cf6",
        "#64748b",
    ]
    income_expense = pd.DataFrame(
        [
            {"Type": "Income", "Amount": income},
            {"Type": "Expense", "Amount": expenses},
        ]
    ).query("Amount > 0")
    expense_categories = (
        period_df.loc[period_df.transaction_type == "Expense"]
        .groupby("category", as_index=False)["amount"]
        .sum()
        .rename(columns={"category": "Category", "amount": "Amount"})
    )

    st.subheader("Spending insights")
    chart_columns = st.columns(2)
    if not income_expense.empty:
        income_expense_chart = (
            alt.Chart(income_expense)
            .mark_arc(innerRadius=76, outerRadius=126, cornerRadius=5, padAngle=0.025)
            .encode(
                theta=alt.Theta("Amount:Q", stack=True),
                color=alt.Color(
                    "Type:N",
                    scale=alt.Scale(
                        domain=["Income", "Expense"], range=["#10b981", "#f97316"]
                    ),
                    legend=alt.Legend(title=None, orient="bottom"),
                ),
                tooltip=[
                    "Type:N",
                    alt.Tooltip("Amount:Q", title="Amount", format=",.2f"),
                ],
            )
            .properties(height=300, title="Income vs. expenses")
            .configure(background="transparent")
            .configure_view(stroke=None)
            .configure_title(color=chart_text, anchor="start", fontSize=15)
            .configure_legend(labelColor=chart_text, labelFontSize=12)
        )
        chart_columns[0].altair_chart(
            income_expense_chart, use_container_width=True, theme="streamlit"
        )
    else:
        chart_columns[0].info("No income or expenses match these filters.")

    if not expense_categories.empty:
        category_chart = (
            alt.Chart(expense_categories)
            .mark_arc(innerRadius=76, outerRadius=126, cornerRadius=5, padAngle=0.025)
            .encode(
                theta=alt.Theta("Amount:Q"),
                color=alt.Color(
                    "Category:N",
                    scale=alt.Scale(range=chart_colors),
                    legend=alt.Legend(title=None, orient="bottom"),
                ),
                tooltip=[
                    "Category:N",
                    alt.Tooltip("Amount:Q", title="Spent", format=",.2f"),
                ],
            )
            .properties(height=300, title="Where your money goes")
            .configure(background="transparent")
            .configure_view(stroke=None)
            .configure_title(color=chart_text, anchor="start", fontSize=15)
            .configure_legend(labelColor=chart_text, labelFontSize=12)
        )
        chart_columns[1].altair_chart(category_chart, use_container_width=True)
    else:
        chart_columns[1].info("No expenses to break down by category.")

    trend = (
        period_df.assign(day=period_df["transaction_date"].dt.date)
        .groupby(["day", "transaction_type"], as_index=False)["amount"]
        .sum()
        .rename(columns={"day": "Date", "transaction_type": "Type", "amount": "Amount"})
    )
    trend_selection = alt.selection_point(fields=["Type"], bind="legend")
    trend_chart = (
        alt.Chart(trend)
        .mark_line(point=alt.OverlayMarkDef(filled=True, size=75), strokeWidth=3)
        .encode(
            x=alt.X("Date:T", title=None),
            y=alt.Y("Amount:Q", title="Amount (₹)", axis=alt.Axis(format="~s")),
            color=alt.Color(
                "Type:N",
                scale=alt.Scale(domain=["Income", "Expense"], range=["#10b981", "#f97316"]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            opacity=alt.condition(trend_selection, alt.value(1), alt.value(0.15)),
            tooltip=["Date:T", "Type:N", alt.Tooltip("Amount:Q", format=",.2f")],
        )
        .add_params(trend_selection)
        .properties(height=280, title="Cash flow over time")
        .interactive()
        .configure(background="transparent")
        .configure_view(stroke=None)
        .configure_title(color=chart_text, anchor="start", fontSize=15)
        .configure_axis(labelColor=chart_text, titleColor=chart_text, gridColor="#94a3b833")
        .configure_legend(labelColor=chart_text)
    )
    st.altair_chart(trend_chart, use_container_width=True, theme="streamlit")

    st.subheader("Transactions")
    with st.expander(f"View matching transactions ({len(period_df)})", expanded=True):
        display_columns = [
            "transaction_date",
            "title",
            "transaction_type",
            "category",
            "amount",
            "description",
        ]
        st.dataframe(
            period_df.sort_values("transaction_date", ascending=False)[display_columns],
            use_container_width=True,
            hide_index=True,
        )
