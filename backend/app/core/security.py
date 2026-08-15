from datetime import datetime, timedelta
import os

import bcrypt
from jose import JWTError, jwt

from fastapi import Depends, HTTPException

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.models.user import User


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development-only-change-me")

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


security = HTTPBearer()


def hash_password(password: str):
    password_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(
    plain_password,
    hashed_password
):
    return bcrypt.checkpw(
        plain_password.encode("utf-8")[:72],
        hashed_password.encode("utf-8")
    )


def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("user_id")

        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user or not user.is_active:

        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return current_user
