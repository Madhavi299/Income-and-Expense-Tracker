from uuid import uuid4

from playwright.sync_api import expect


def test_logged_out_visitors_only_see_login_page(browser_page, e2e_services):
    page = browser_page
    page.goto(
        f"{e2e_services['frontend_url']}/admin",
        wait_until="domcontentloaded",
    )

    expect(page.get_by_role("tab", name="Login")).to_be_visible()
    expect(page.locator("input[aria-label='Email']:visible")).to_be_visible()
    expect(page.get_by_role("link", name="admin", exact=True)).to_have_count(0)
    expect(
        page.get_by_role("link", name="add transaction", exact=True)
    ).to_have_count(0)


def test_add_dashboard_view_and_manage_transactions(
    browser_page, e2e_services, capture_page
):
    page = browser_page
    unique_id = uuid4().hex[:8]
    username = f"flow_{unique_id}"
    email = f"{username}@example.com"
    password = "secure-password"
    expense_title = f"Playwright Groceries {unique_id}"
    income_title = f"Playwright Salary {unique_id}"
    edited_title = f"Playwright Edited Groceries {unique_id}"

    page.get_by_role("tab", name="Create account").click()
    page.get_by_label("Username").fill(username)
    page.locator("input[aria-label='Email']:visible").fill(email)
    page.get_by_label("Password (at least 8 characters)").fill(password)
    page.get_by_label("Confirm password").fill(password)
    page.get_by_role("button", name="Create account").click()
    expect(page.get_by_text("Account created. Please log in.")).to_be_visible()

    page.get_by_role("tab", name="Login").click()
    capture_page("login-page")
    page.locator("input[aria-label='Email']:visible").fill(email)
    page.locator("input[aria-label='Password']:visible").fill(password)
    page.get_by_role("button", name="Login").click()
    expect(page.get_by_text(f"Logged in as {username}")).to_be_visible(timeout=10_000)
    capture_page("dashboard-after-login")

    page.get_by_role("link", name="Add Transaction").click()
    expect(page.get_by_role("heading", name="➕ Add Transaction")).to_be_visible()
    page.get_by_label("Title").fill(expense_title)
    page.get_by_label("Amount (₹)").fill("125")
    page.get_by_role("button", name="Save Transaction").click()
    expect(page.get_by_text("Transaction saved to the database.")).to_be_visible()

    page.get_by_label("Title").fill(income_title)
    page.get_by_label("Amount (₹)").fill("1000")
    page.get_by_role("combobox", name="Transaction type").click()
    page.get_by_role("option", name="Income").click()
    page.get_by_role("button", name="Save Transaction").click()
    expect(page.get_by_text("Transaction saved to the database.")).to_be_visible()
    capture_page("add-transaction-page")

    page.get_by_role("link", name="Dashboard").click()
    expect(page.get_by_role("heading", name="📊 Dashboard")).to_be_visible()
    expect(page.get_by_text("₹1,000.00")).to_be_visible()
    expect(page.get_by_text("₹125.00")).to_be_visible()
    balance_metric = page.get_by_test_id("stMetric").filter(has_text="Balance")
    expect(balance_metric).to_contain_text("₹875.00")
    capture_page("dashboard-totals")

    page.get_by_role("link", name="View Transactions").click()
    expect(page.get_by_role("heading", name="📄 View Transactions")).to_be_visible()
    transaction_grid = page.get_by_test_id("stDataFrame")
    expect(transaction_grid).to_contain_text(expense_title, timeout=15_000)
    expect(transaction_grid).to_contain_text(income_title, timeout=15_000)
    capture_page("view-transactions-page")
    search = page.get_by_label("Search title, category, or description")
    search.fill(expense_title)
    search.press("Enter")
    expect(transaction_grid).to_contain_text(expense_title)
    expect(transaction_grid).not_to_contain_text(income_title)
    capture_page("view-transactions-search")

    page.get_by_role("link", name="Manage Transactions").click()
    expect(page.get_by_role("heading", name="🛠️ Manage Transactions")).to_be_visible()
    page.get_by_role("combobox", name="Select a transaction").click()
    page.get_by_role("option", name=expense_title).click()
    title_input = page.get_by_label("Title")
    expect(title_input).to_have_value(expense_title)
    title_input.fill(edited_title)
    page.get_by_role("button", name="Save Transaction").click()
    expect(page.get_by_role("combobox", name="Select a transaction")).to_be_visible()

    login_response = page.request.post(
        f"{e2e_services['api_url']}/auth/login",
        data={"email": email, "password": password},
    )
    assert login_response.status == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    transactions = []
    for _ in range(20):
        transactions_response = page.request.get(
            f"{e2e_services['api_url']}/transactions", headers=headers
        )
        assert transactions_response.status == 200
        transactions = transactions_response.json()
        if edited_title in {transaction["title"] for transaction in transactions}:
            break
        page.wait_for_timeout(250)
    assert edited_title in {transaction["title"] for transaction in transactions}
    capture_page("manage-transactions-after-edit")

    page.get_by_text(
        "I confirm I want to delete this transaction.", exact=True
    ).click()
    expect(page.get_by_role("button", name="Delete Transaction")).to_be_enabled()
    page.get_by_role("button", name="Delete Transaction").click()
    transactions_response = page.request.get(
        f"{e2e_services['api_url']}/transactions", headers=headers
    )
    assert transactions_response.status == 200
    transactions = transactions_response.json()
    titles = {transaction["title"] for transaction in transactions}
    assert edited_title in titles
    assert income_title not in titles
    capture_page("manage-transactions-after-delete")


def test_registration_login_and_dashboard_navigation(browser_page, e2e_services):
    page = browser_page
    page.goto(e2e_services["frontend_url"], wait_until="domcontentloaded")

    page.get_by_role("tab", name="Create account").click()
    page.get_by_label("Username").fill("e2e_user")
    page.locator("input[aria-label='Email']:visible").fill("e2e-user@example.com")
    page.get_by_label("Password (at least 8 characters)").fill("secure-password")
    page.get_by_label("Confirm password").fill("secure-password")
    page.get_by_role("button", name="Create account").click()
    expect(page.get_by_text("Account created. Please log in.")).to_be_visible(
        timeout=10_000
    )

    page.get_by_role("tab", name="Login").click()
    page.locator("input[aria-label='Email']:visible").fill("unknown@example.com")
    page.locator("input[aria-label='Password']:visible").fill("secure-password")
    page.get_by_role("button", name="Login").click()
    expect(
        page.get_by_text("Account not found. Please create an account first.")
    ).to_be_visible(timeout=10_000)

    page.locator("input[aria-label='Email']:visible").fill("e2e-user@example.com")
    page.locator("input[aria-label='Password']:visible").fill("wrong-password")
    page.get_by_role("button", name="Login").click()
    expect(page.get_by_text("Incorrect password. Please try again.")).to_be_visible(
        timeout=10_000
    )

    page.locator("input[aria-label='Password']:visible").fill("secure-password")
    page.get_by_role("button", name="Login").click()
    expect(page.get_by_text("Logged in as e2e_user")).to_be_visible(timeout=10_000)
    expect(page.get_by_role("heading", name="📊 Dashboard")).to_be_visible(
        timeout=10_000
    )
