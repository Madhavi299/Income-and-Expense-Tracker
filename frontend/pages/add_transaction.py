from datetime import date

import streamlit as st

from frontend.api_client import APIError, create_transaction, extract_bill

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


def _save_transaction(token, title, amount, kind, category, tx_date, description, source):
    create_transaction(
        token,
        {
            "title": title.strip(),
            "amount": amount,
            "transaction_type": kind,
            "category": category,
            "transaction_date": tx_date.isoformat(),
            "description": description,
            "source": source,
        },
    )


def page():
    st.title("➕ Add Transaction")
    st.caption("Keep your records up to date, or let a bill image do the data entry.")
    token = st.session_state.token

    st.markdown("#### Choose how to add a record")
    manual_tab, bill_tab = st.tabs(["✍️  Enter details", "🧾  Scan a bill"])
    with manual_tab:
        with st.container(border=True):
            st.markdown("#### Transaction details")
            st.caption(
                "Record money coming in or going out. You can edit these details later."
            )
            with st.form("manual_transaction_form"):
                kind = st.selectbox("Transaction type", ["Expense", "Income"])
                title = st.text_input(
                    "Title",
                    placeholder="e.g. Monthly salary or groceries",
                )
                columns = st.columns(2)
                amount = columns[0].number_input(
                    "Amount (₹)", min_value=0.01, step=100.0, format="%.2f"
                )
                category = columns[1].selectbox("Category", CATEGORIES)
                tx_date = st.date_input("Transaction date", value=date.today())
                description = st.text_area(
                    "Note (optional)", placeholder="Add a short note for future reference"
                )
                submitted = st.form_submit_button(
                    "Save Transaction", use_container_width=True
                )

        if submitted:
            if not title.strip():
                st.error("Please enter a title.")
            else:
                try:
                    with st.spinner("Saving transaction…"):
                        _save_transaction(
                            token,
                            title,
                            amount,
                            kind,
                            category,
                            tx_date,
                            description,
                            "manual",
                        )
                    st.success("Transaction saved to the database.")
                    st.toast("Your transaction has been added.", icon="✅")
                except APIError as exc:
                    st.error(str(exc))

    with bill_tab:
        with st.container(border=True):
            st.markdown("#### Turn a bill into a transaction")
            st.caption(
                "Upload a clear image or PDF. We’ll suggest details for you to review."
            )
            uploaded = st.file_uploader(
                "Choose a bill image or PDF",
                type=["pdf", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
                key="bill_upload",
            )
            if uploaded is not None:
                st.caption(
                    f"Selected: {uploaded.name} · {uploaded.size / 1024:.0f} KB"
                )
            if st.button(
                "Extract bill details",
                disabled=uploaded is None,
                use_container_width=True,
            ):
                try:
                    with st.spinner("Reading bill details…"):
                        result = extract_bill(token, uploaded)
                    st.session_state.bill_fields = result["fields"]
                    st.session_state.bill_text = result["extracted_text"]
                    st.success("Extraction complete. Review the suggested details below.")
                except APIError as exc:
                    st.error(str(exc))

        fields = st.session_state.get("bill_fields")
        if fields:
            st.markdown("#### Review extracted details")
            if st.session_state.get("bill_text"):
                with st.expander("See extracted text"):
                    st.text(st.session_state.bill_text)
            raw_amount = fields.get("amount")
            try:
                default_date = date.fromisoformat(
                    fields.get("transaction_date", date.today().isoformat())
                )
            except ValueError:
                default_date = date.today()
            detected_category = fields.get("category", "Other")
            category_index = (
                CATEGORIES.index(detected_category)
                if detected_category in CATEGORIES
                else CATEGORIES.index("Other")
            )
            with st.container(border=True):
                with st.form("save_bill_transaction_form"):
                    title = st.text_input(
                        "Bill or merchant name",
                        value=fields.get("title") or "Uploaded bill",
                    )
                    columns = st.columns(2)
                    amount = columns[0].number_input(
                        "Total amount (₹)",
                        min_value=0.0,
                        value=float(raw_amount or 0.0),
                        step=10.0,
                        format="%.2f",
                    )
                    kind = columns[1].selectbox(
                        "Transaction type", ["Expense", "Income"], index=0
                    )
                    category = st.selectbox(
                        "Category", CATEGORIES, index=category_index
                    )
                    tx_date = st.date_input("Transaction date", value=default_date)
                    description = st.text_area(
                        "Description or extracted text",
                        value=fields.get("description", "")[:4000],
                    )
                    save = st.form_submit_button(
                        "Save reviewed transaction", use_container_width=True
                    )
            if save:
                if not title.strip():
                    st.error("Please enter a bill title.")
                elif amount <= 0:
                    st.error("Enter a valid bill total before saving.")
                else:
                    try:
                        _save_transaction(
                            token,
                            title,
                            amount,
                            kind,
                            category,
                            tx_date,
                            description,
                            "bill_ocr",
                        )
                        st.success("Bill transaction saved to your database.")
                        st.session_state.pop("bill_fields", None)
                        st.session_state.pop("bill_text", None)
                        st.rerun()
                    except APIError as exc:
                        st.error(str(exc))
