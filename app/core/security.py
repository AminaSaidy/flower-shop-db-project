import hashlib
import hmac
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Header
from jose import JWTError, jwt
from app.core.config import settings


def create_access_token(user_id: str) -> str:
    expire  = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
