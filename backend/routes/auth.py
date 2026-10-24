"""
Authentication API Endpoints.
Handles User Registration, Login, and Current Profile Resolution.
"""

from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, UserProfile
from backend.auth import hash_password, verify_password, create_access_token, get_required_user, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user account with hashed password."""
    clean_email = payload.email.strip().lower()

    if len(payload.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    # Check if user already exists
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    hashed = hash_password(payload.password)
    new_user = User(
        email=clean_email,
        hashed_password=hashed,
        full_name=payload.full_name.strip() if payload.full_name else clean_email.split("@")[0]
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create empty profile associated with user
    profile = UserProfile(user_id=new_user.id)
    db.add(profile)
    db.commit()

    token = create_access_token({"sub": str(new_user.id), "email": new_user.email})

    return {
        "success": True,
        "message": "Account created successfully!",
        "access_token": token,
        "token_type": "bearer",
        "user": new_user.to_dict()
    }


@router.post("/login")
def login_user(payload: LoginRequest, db: Session = Depends(get_db)):
    """Logs in an existing user and returns a signed JWT token."""
    clean_email = payload.email.strip().lower()

    user = db.query(User).filter(User.email == clean_email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated."
        )

    token = create_access_token({"sub": str(user.id), "email": user.email})

    return {
        "success": True,
        "message": f"Welcome back, {user.full_name or user.email}!",
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict()
    }


@router.get("/me")
def get_me(user: User = Depends(get_required_user)):
    """Returns currently logged-in user details and profile summary."""
    prof = user.profile.to_candidate_schema() if user.profile else None
    return {
        "user": user.to_dict(),
        "candidate_profile": prof
    }
