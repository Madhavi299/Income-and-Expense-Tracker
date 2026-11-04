# Personal Income & Expense Tracker (New Project)

This is a separate project. It does not modify your existing tracker.

## Features
- Register and log in with separate user accounts
- Passwords hashed using PBKDF2 (Python standard library)
- JWT authentication for the FastAPI backend
- Each user can see and manage only their own transactions
- Role-based access for regular users and administrators, including account activation controls and activity monitoring
- Dashboard, add transaction, view transactions, and manage transactions pages
- Upload an image/PDF bill, extract text, detect likely amount/date/merchant/category, review the fields, then save to the database
- PostgreSQL supported; SQLite is the default for a simple first run

## 1. Create and activate a virtual environment (Windows PowerShell)
```powershell
cd personal_income_expense_tracker_login
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Configure environment
Copy `.env.example` to `.env` and set a unique `SECRET_KEY`.
To bootstrap the first administrator, also set `INITIAL_ADMIN_EMAIL` and a
strong `INITIAL_ADMIN_PASSWORD` before starting the backend. The backend creates
that admin only when the email and username are unused; it never promotes an
existing user or resets the password of an already bootstrapped account.
On startup, existing databases are migrated with `role` and `is_active`
columns; existing accounts remain active regular users.
If the email belongs to an account you control and you want to make that
account the first admin, set `INITIAL_ADMIN_PROMOTE_EXISTING=true` for one
startup. The account must be active and keeps its existing password; this
setting does not reset passwords. Set it back to `false` after the promotion.
For the easiest first run, keep the SQLite DATABASE_URL in `.env.example`.
For PostgreSQL, set DATABASE_URL to your PostgreSQL connection string, for example:
`postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/expense_tracker`

Change SECRET_KEY to a long random value before using this beyond local testing.

## 3. Start the backend
Open Terminal 1 in the project folder:
```powershell
uvicorn backend.app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

## 4. Start the Streamlit frontend
Open Terminal 2 in the same project folder:
```powershell
streamlit run frontend/app.py
```
Streamlit opens at http://localhost:8501.

## 5. Deploy to Streamlit Community Cloud

The Streamlit app is the frontend; the FastAPI backend and a persistent PostgreSQL
database must also be hosted publicly. The included `Dockerfile` and `render.yaml`
provide a Render deployment for the API. Use a managed PostgreSQL provider such as
Neon for `DATABASE_URL`; do not use the default SQLite database on an ephemeral
cloud filesystem for real user data.

1. Create an empty repository on GitHub (without adding a README), then from
   this project folder run:

   ```powershell
   git init -b main
   git add .
   git commit -m "Prepare app for cloud deployment"
   git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
   git push -u origin main
   ```

   Replace the remote URL with your repository's URL. Do not commit `.env` or
   `.streamlit/secrets.toml`; they are excluded by `.gitignore`.
2. Create a PostgreSQL database with your database provider and copy its
   connection string. Keep it private.
3. In Render, create a Blueprint from the GitHub repository and deploy the
   `expense-tracker-api` service. When prompted, set `DATABASE_URL` to the
   PostgreSQL connection string and provide `INITIAL_ADMIN_EMAIL` and a unique,
   strong `INITIAL_ADMIN_PASSWORD` for the first administrator. Render generates
   `SECRET_KEY` for the API.
   The deployed API health check is its root URL; it should return a JSON
   message that the API is running.
4. In Streamlit Community Cloud, create an app from the same repository and
   select `frontend/app.py` as the app file.
5. In the Streamlit app's **Settings > Secrets**, add the public API URL:

   ```toml
   API_BASE_URL = "https://your-api-service.onrender.com"
   ```

   Save the secret and reboot the Streamlit app. For local use, `API_BASE_URL`
   can instead be set in `.env`.

Administrators use the same login form as regular users and are routed to the
Admin Console. It supports paginated account viewing, role assignment,
activation/deactivation, and a recent activity feed. If the bootstrap email
already belongs to a regular account, startup fails instead of granting
administrator access; choose a fresh email or promote that account manually
through a trusted database session. Keep the bootstrap password private and do
not commit it to GitHub.

The free Render service may sleep when idle, so the first API request after a
period of inactivity can take longer. Use a persistent managed database and
review the hosting providers' current pricing, backups, and service limits
before storing important financial records.

## 6. Run the test suite
Install the test dependencies, Playwright's Chromium browser, and FFmpeg.
FFmpeg must be available on `PATH` to convert browser recordings to MP4.
In PowerShell, run the tests in headed mode so the browser is visible:
```powershell
pip install -r requirements-dev.txt
python -m playwright install chromium
$env:PLAYWRIGHT_HEADLESS = "false"
python -m pytest -v -s playwright\tests
```
The suite contains seven test categories: unit, API, database integration,
browser E2E, regression, load-smoke, and security. The E2E tests exercise
account registration and login, add income and expense transactions, verify
dashboard totals, search and view transactions, and edit and delete
transactions.

The tests start isolated local backend and frontend processes and use a
temporary database. They do not use or modify your configured application
database. Results are grouped by outcome:
- `playwright/artifacts/pass/screenshots/` and `playwright/artifacts/pass/videos/`
- `playwright/artifacts/fail/screenshots/` and `playwright/artifacts/fail/videos/`
- `playwright/artifacts/logs/` contains E2E backend and frontend logs.

Screenshots are timestamped, show the real project page with a PASS or FAIL
banner, and include a separate capture for each page checkpoint in the CRUD
workflow. Each test also gets a matching MP4 recording in its outcome folder.
Run a single category, for example:
```powershell
python -m pytest -v -s playwright\tests\test_e2e.py
```

## Bill OCR notes
- Install Tesseract OCR for image bills and set `TESSERACT_CMD` in `.env` if it is not on PATH.
- PDF text is read directly first. Scanned PDFs may need Tesseract plus Poppler installed for PDF-to-image conversion. If PDF OCR dependencies are missing, use a clear photo/image of the bill or install the optional tools listed below.
- OCR is imperfect. Review and correct extracted fields before saving. The app does not silently save unreviewed OCR results.
