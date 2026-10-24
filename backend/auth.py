"""
Authentication & JWT Utilities for Multi-User Management.
Provides password hashing via bcrypt, JWT token creation, and FastAPI user resolution.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

try:
    import jwt
    HAS_JWT = True
except ImportError:
    HAS_JWT = False

import hashlib
import secrets
import json
import base64
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, UserProfile

# Secret key for JWT signing (uses environment variable if provided, fallback to stable internal key)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jobhunter-super-secret-production-jwt-key-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Hashes a raw password securely using bcrypt with pbkdf2 fallback."""
    if HAS_BCRYPT:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2:{salt}:{key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored hash."""
    try:
        if hashed_password.startswith("pbkdf2:"):
            parts = hashed_password.split(":")
            if len(parts) == 3:
                salt = parts[1]
                expected_hex = parts[2]
                computed = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
                return secrets.compare_digest(computed.hex(), expected_hex)
        if HAS_BCRYPT:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        return False
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed JWT or HMAC access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": int(expire.timestamp()), "iat": int(datetime.utcnow().timestamp())})
    if HAS_JWT:
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    payload_str = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).decode()
    sig = hashlib.sha256((payload_str + JWT_SECRET_KEY).encode()).hexdigest()
    return f"{payload_str}.{sig}"


def decode_access_token(token: str) -> Optional[dict]:
    """Decodes and validates an access token."""
    try:
        if HAS_JWT and "." in token and token.count(".") == 2:
            return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if "." in token:
            payload_str, sig = token.split(".", 1)
            expected_sig = hashlib.sha256((payload_str + JWT_SECRET_KEY).encode()).hexdigest()
            if not secrets.compare_digest(sig, expected_sig):
                return None
            data = json.loads(base64.urlsafe_b64decode(payload_str.encode()).decode())
            if data.get("exp") and data["exp"] < int(datetime.utcnow().timestamp()):
                return None
            return data
        return None
    except Exception:
        return None


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Resolves the currently authenticated user from the Bearer token.
    Returns None if no token or invalid token is supplied (allows guest fallback).
    """
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    return user


def get_required_user(user: Optional[User] = Depends(get_current_user)) -> User:
    """Requires authentication. Raises HTTP 401 if not logged in."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
