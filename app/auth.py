from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class TokenData(BaseModel):
    user_id: int
    email: str
    family_id: int
    role: str


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: int, email: str, family_id: int, role: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_expiry_seconds)
    payload = {
        "user_id": user_id,
        "email": email,
        "family_id": family_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "wealthwatch",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> TokenData:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return TokenData(
            user_id=payload["user_id"],
            email=payload["email"],
            family_id=payload["family_id"],
            role=payload["role"],
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    return decode_token(credentials.credentials)


def require_role(*allowed: str):
    def dependency(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if current_user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return dependency
