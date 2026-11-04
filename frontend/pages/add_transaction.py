from datetime import date
import streamlit as st
from frontend.api_client import APIError, create_transaction, extract_bill

def page():
    st.title("➕ Add Transaction")
    st.caption("Enter details manually or upload a bill and review the extracted fields.")
    token = st.session_state.token

    manual_tab, bill_tab = st.tabs(["Enter manually", "🧾 Upload a bill"])
    with manual_tab:
        with st.form("manual_transaction_form"):
            title = st.text_input("Title")
            amount = st.number_input("Amount (₹)", min_value=0.01, step=10.0, format="%.2f")
            kind = st.selectbox("Transaction type", ["Expense", "Income"])
            category = st.selectbox("Category", ["Food", "Groceries", "Transport", "Utilities", "Healthcare", "Shopping", "Education", "Salary", "Other"])
            tx_date = st.date_input("Transaction date", value=date.today())
            description = st.text_area("Description (optional)")
            submitted = st.form_submit_button("Save Transaction", use_container_width=True)
        if submitted:
            if not title.strip():
                st.error("Please enter a title.")
            else:
                try:
                    create_transaction(token, {"title": title.strip(), "amount": amount, "transaction_type": kind, "category": category, "transaction_date": tx_date.isoformat(), "description": description, "source": "manual"})
                    st.success("Transaction saved to the database.")
                except APIError as exc:
                    st.error(str(exc))

    with bill_tab:
        st.subheader("Upload a bill")
        st.write("Upload a clear bill image or PDF. The app extracts text and suggests fields. Review them before saving.")
        uploaded = st.file_uploader("Choose bill file", type=["pdf", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"], key="bill_upload")
        if st.button("Extract bill data", disabled=uploaded is None, use_container_width=True):
            try:
                result = extract_bill(token, uploaded)
                st.session_state.bill_fields = result["fields"]
                st.session_state.bill_text = result["extracted_text"]
                st.success("Text extracted. Review the suggested fields below.")
            except APIError as exc:
                st.error(str(exc))

        fields = st.session_state.get("bill_fields")
        if fields:
            st.markdown("### Review extracted details")
            if st.session_state.get("bill_text"):
                with st.expander("View all extracted text"):
                    st.text(st.session_state.bill_text)
            with st.form("save_bill_transaction_form"):
                title = st.text_input("Bill / merchant name", value=fields.get("title") or "Uploaded bill")
                raw_amount = fields.get("amount")
                amount = st.number_input("Total amount (₹)", min_value=0.0, value=float(raw_amount or 0.0), step=10.0, format="%.2f")
                kind = st.selectbox("Transaction type", ["Expense", "Income"], index=0)
                categories = ["Food", "Groceries", "Transport", "Utilities", "Healthcare", "Shopping", "Education", "Salary", "Other"]
                detected_category = fields.get("category", "Other")
                category_index = categories.index(detected_category) if detected_category in categories else categories.index("Other")
                category = st.selectbox("Category", categories, index=category_index)
                try:
                    default_date = date.fromisoformat(fields.get("transaction_date", date.today().isoformat()))
                except ValueError:
                    default_date = date.today()
                tx_date = st.date_input("Transaction date", value=default_date)
                description = st.text_area("Description / extracted text", value=fields.get("description", "")[:4000])
                save = st.form_submit_button("Save Bill Transaction to Database", use_container_width=True)
            if save:
                if not title.strip():
                    st.error("Please enter a bill title.")
                elif amount <= 0:
                    st.error("Could not detect a valid amount. Enter the bill total manually.")
                else:
                    try:
                        create_transaction(token, {"title": title.strip(), "amount": amount, "transaction_type": kind, "category": category, "transaction_date": tx_date.isoformat(), "description": description, "source": "bill_ocr"})
                        st.success("Bill transaction saved to your database.")
                        st.session_state.pop("bill_fields", None)
                        st.session_state.pop("bill_text", None)
                        st.rerun()
                    except APIError as exc:
                        st.error(str(exc))
