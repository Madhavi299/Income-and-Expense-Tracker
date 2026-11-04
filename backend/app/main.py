from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.app.activity import record_activity
from backend.app.core.config import (
    INITIAL_ADMIN_EMAIL,
    INITIAL_ADMIN_PASSWORD,
    INITIAL_ADMIN_PROMOTE_EXISTING,
    INITIAL_ADMIN_USERNAME,
)
from backend.app.db.database import SessionLocal, initialize_database
from backend.app import models  # noqa: F401 - registers SQLAlchemy models
from backend.app.models import ActivityLog, User
from backend.app.routers.auth import router as auth_router
from backend.app.routers.admin import router as admin_router
from backend.app.routers.transactions import router as transactions_router
from backend.app.routers.bills import router as bills_router
from backend.app.security import hash_password

def ensure_initial_admin():
    if not INITIAL_ADMIN_EMAIL and not INITIAL_ADMIN_PASSWORD:
        return
    if not INITIAL_ADMIN_EMAIL or not INITIAL_ADMIN_PASSWORD:
        raise RuntimeError(
            "Set both INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD to bootstrap an administrator."
        )
    if len(INITIAL_ADMIN_PASSWORD) < 8:
        raise RuntimeError("INITIAL_ADMIN_PASSWORD must contain at least 8 characters.")
    if len(INITIAL_ADMIN_USERNAME) < 3 or len(INITIAL_ADMIN_USERNAME) > 80:
        raise RuntimeError("INITIAL_ADMIN_USERNAME must contain 3 to 80 characters.")

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == INITIAL_ADMIN_EMAIL).first()
        if user:
            was_bootstrapped = (
                db.query(ActivityLog.id)
                .filter(
                    ActivityLog.action.in_(
                        ["initial_admin_created", "initial_admin_promoted"]
                    ),
                    ActivityLog.target_user_id == user.id,
                )
                .first()
            )
            if user.role != "admin":
                if was_bootstrapped:
                    return
                if not INITIAL_ADMIN_PROMOTE_EXISTING:
                    raise RuntimeError(
                        "The initial admin email already belongs to a non-admin account. "
                        "Set INITIAL_ADMIN_PROMOTE_EXISTING=true to promote this exact "
                        "account, or choose an unused email."
                    )
                if not user.is_active:
                    raise RuntimeError(
                        "The initial admin account is inactive. Activate it before "
                        "promoting it."
                    )
                user.role = "admin"
                record_activity(
                    db,
                    "initial_admin_promoted",
                    target_user_id=user.id,
                    details="Existing account promoted by deployment configuration",
                )
                db.commit()
            return
        username_owner = db.query(User.id).filter(
            User.username == INITIAL_ADMIN_USERNAME
        ).first()
        if username_owner:
            raise RuntimeError(
                "INITIAL_ADMIN_USERNAME is already in use. Choose a unique username."
            )
        user = User(
            username=INITIAL_ADMIN_USERNAME,
            email=INITIAL_ADMIN_EMAIL,
            password_hash=hash_password(INITIAL_ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.flush()
        record_activity(
            db,
            "initial_admin_created",
            actor_user_id=user.id,
            target_user_id=user.id,
        )
        db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    ensure_initial_admin()
    yield

app = FastAPI(title="Personal Income & Expense Tracker API", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(transactions_router)
app.include_router(bills_router)

@app.get("/")
def root():
    return {"message": "Personal Income & Expense Tracker API is running"}
