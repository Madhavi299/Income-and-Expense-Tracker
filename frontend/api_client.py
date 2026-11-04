import os
import requests
import streamlit as st
from dotenv import load_dotenv
from streamlit.errors import StreamlitSecretNotFoundError

load_dotenv()
TIMEOUT = 30

class APIError(Exception):
    pass

def _api_base_url():
    api_base_url = os.getenv("API_BASE_URL")
    if not api_base_url:
        try:
            api_base_url = st.secrets.get("API_BASE_URL")
        except StreamlitSecretNotFoundError:
            api_base_url = None
    return (api_base_url or "http://127.0.0.1:8000").rstrip("/")

def _request(method, path, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(method, f"{_api_base_url()}{path}", headers=headers, timeout=TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        raise APIError("Cannot connect to the backend. Start it with: uvicorn backend.app.main:app --reload") from exc
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise APIError(str(detail))
    if response.status_code == 204:
        return None
    return response.json()

def register(username, email, password):
    return _request("POST", "/auth/register", json={"username": username, "email": email, "password": password})

def login(email, password):
    return _request("POST", "/auth/login", json={"email": email, "password": password})

def current_user(token):
    return _request("GET", "/auth/me", token=token)

def list_transactions(token):
    return _request("GET", "/transactions", token=token)

def create_transaction(token, data):
    return _request("POST", "/transactions", token=token, json=data)

def update_transaction(token, transaction_id, data):
    return _request("PATCH", f"/transactions/{transaction_id}", token=token, json=data)

def delete_transaction(token, transaction_id):
    return _request("DELETE", f"/transactions/{transaction_id}", token=token)

def extract_bill(token, uploaded_file):
    return _request("POST", "/bills/extract", token=token, files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "application/octet-stream")})

def list_admin_users(token, limit=500, offset=0):
    return _request(
        "GET",
        "/admin/users",
        token=token,
        params={"limit": limit, "offset": offset},
    )

def update_admin_user(token, user_id, data):
    return _request("PATCH", f"/admin/users/{user_id}", token=token, json=data)

def list_activity(token, limit=200):
    return _request(
        "GET",
        "/admin/activity",
        token=token,
        params={"limit": limit},
    )
