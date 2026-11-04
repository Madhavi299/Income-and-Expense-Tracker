from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from backend.app.core.config import SECRET_KEY, ALGORITHM
from backend.app.db.database import get_db
from backend.app.models import User

bearer = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Please log in")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", ""))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired login token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User account not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is deactivated")
    return user

def get_current_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user

def get_current_regular_user(user: User = Depends(get_current_user)):
    if user.role != "user":
        raise HTTPException(status_code=403, detail="A user account is required")
    return user
