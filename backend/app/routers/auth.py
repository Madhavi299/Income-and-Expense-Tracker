from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
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
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found. Please create an account first.")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password. Please try again.")
    return {"access_token": create_access_token(user.id), "token_type": "bearer", "user": user}

@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
