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

def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return {"user_id": payload["sub"]}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


