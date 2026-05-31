from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.calendar import CalendarMember
from app.models.user import User
from app.utils.jwt import verify_access_token

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """从 JWT Token 中解析当前用户"""
    token = credentials.credentials
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return user


def require_member(calendar_id: int, user: User, db: Session) -> None:
    """检查用户是否为日历成员，不是则抛出 NotMember"""
    exists = (
        db.query(CalendarMember)
        .filter(
            CalendarMember.calendar_id == calendar_id,
            CalendarMember.user_id == user.id,
        )
        .first()
    )
    if not exists:
        from app.exceptions import NotMember

        raise NotMember()
