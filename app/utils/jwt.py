from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings


def create_access_token(user_id: int) -> str:
    """生成 JWT Token"""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    payload = {
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def verify_access_token(token: str) -> int | None:
    """验证 JWT Token，返回 user_id 或 None"""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload.get("user_id")
    except JWTError:
        return None
