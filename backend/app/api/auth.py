from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth_utils import create_token, current_user, hash_password, verify_password
from app.config import settings
from app.db import get_db
from app.models import User
from app.schemas import LoginIn, RegisterIn, TokenOut

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def tokens_for(user: User) -> TokenOut:
    access = create_token(user)
    refresh = create_token(user, minutes=settings.jwt_expire_minutes * 2)
    return TokenOut(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password too short")
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        language=body.language,
        is_admin=email == settings.admin_email.lower(),
    )
    db.add(user)
    db.flush()
    return tokens_for(user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=body.email.strip().lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return tokens_for(user)


@router.post("/refresh", response_model=TokenOut)
def refresh(user: User = Depends(current_user)):
    return tokens_for(user)
