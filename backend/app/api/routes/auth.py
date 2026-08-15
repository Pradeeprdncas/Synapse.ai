from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)

from app.models.user import User
from app.schemas.user import ProfileUpdate, UserCreate, UserLogin

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    new_user = User(
        name=user.name,
        email=user.email,
        password=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully"
    }


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if not existing_user:
        raise HTTPException(
            status_code=400,
            detail="Invalid credentials"
        )

    valid_password = verify_password(
        user.password,
        existing_user.password
    )
    if not valid_password:
        raise HTTPException(
            status_code=400,
            detail="Invalid credentials"
        )

    token = create_access_token(
        {
            "user_id": existing_user.id,
            "email": existing_user.email
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role
    }


@router.patch("/me")
def update_me(payload: ProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    values = payload.model_dump(exclude_unset=True)
    if "email" in values and values["email"] != current_user.email:
        if db.query(User).filter(User.email == values["email"], User.id != current_user.id).first():
            raise HTTPException(409, "Email already exists")
        current_user.email = values["email"]
    if "name" in values:
        current_user.name = values["name"].strip()
    if values.get("new_password"):
        if not values.get("current_password") or not verify_password(values["current_password"], current_user.password):
            raise HTTPException(400, "Current password is incorrect")
        current_user.password = hash_password(values["new_password"])
    db.commit(); db.refresh(current_user)
    return {"id": current_user.id, "email": current_user.email, "name": current_user.name, "role": current_user.role}
