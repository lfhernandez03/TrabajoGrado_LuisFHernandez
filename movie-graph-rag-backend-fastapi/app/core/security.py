from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, email: str) -> str:
    expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"sub": subject, "email": email, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, str]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        subject = payload.get("sub")
        email = payload.get("email")
        if not subject or not email:
            raise ValueError("Invalid token payload")
        return {"sub": subject, "email": email}
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
