from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.activity import record_activity
from backend.app.db.database import get_db
from backend.app.models import User
from backend.app.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from backend.app.security import hash_password, verify_password, create_access_token
from backend.app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.query(User).filter((User.email == email) | (User.username == data.username)).first():
        raise HTTPException(status_code=409, detail="Email or username is already registered")
    user = User(username=data.username.strip(), email=email, password_hash=hash_password(data.password))
    db.add(user)
    db.flush()
    record_activity(db, "user_registered", actor_user_id=user.id, target_user_id=user.id)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user:
        record_activity(db, "login_failed", details="Invalid credentials")
        db.commit()
        raise HTTPException(status_code=404, detail="Account not found. Please create an account first.")
    if not verify_password(data.password, user.password_hash):
        record_activity(
            db,
            "login_failed",
            target_user_id=user.id,
            details="Invalid credentials",
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Incorrect password. Please try again.")
    if not user.is_active:
        record_activity(
            db,
            "login_blocked_inactive",
            target_user_id=user.id,
            details="Inactive account login attempt",
        )
        db.commit()
        raise HTTPException(status_code=403, detail="This account is deactivated")
    record_activity(db, "login_succeeded", actor_user_id=user.id, target_user_id=user.id)
    db.commit()
    return {"access_token": create_access_token(user.id), "token_type": "bearer", "user": user}

@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
