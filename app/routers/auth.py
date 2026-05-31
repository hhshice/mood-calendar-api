import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UpdateUserRequest, UserInfo
from app.utils.jwt import create_access_token
from app.utils.wechat import code2session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=dict)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    微信登录

    用 wx.login() 获取的 code 换取 openid，自动注册或登录用户。
    开发阶段：未配置 AppID/Secret 时自动使用 mock openid。
    """
    # 调用微信 code2Session 获取 openid
    try:
        session = code2session(request.code)
        openid = session["openid"]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WECHAT_AUTH_FAILED", "message": str(e)},
        )

    # 查找或创建用户
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        # 新用户：用 openid 后几位生成默认昵称
        short_id = openid[-8:] if len(openid) > 8 else openid
        user = User(
            openid=openid,
            nickname=f"用户{short_id}",
            avatar="",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"新用户注册: id={user.id}, openid={short_id}")

    token = create_access_token(user_id=user.id)

    return {
        "data": LoginResponse(
            token=token,
            user=UserInfo(id=user.id, nickname=user.nickname, avatar=user.avatar),
        ).model_dump()
    }


@router.patch("/users/me", response_model=dict)
def update_profile(
    request: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户昵称/头像"""
    if request.nickname is not None:
        current_user.nickname = request.nickname
    if request.avatar is not None:
        current_user.avatar = request.avatar
    db.commit()
    db.refresh(current_user)

    return {
        "data": UserInfo(
            id=current_user.id,
            nickname=current_user.nickname,
            avatar=current_user.avatar,
        ).model_dump()
    }
