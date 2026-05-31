from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import NotAuthorized, NotFound, NotMember
from app.models.calendar import CalendarMember
from app.models.comment import Comment
from app.models.mood_entry import MoodEntry
from app.models.user import User
from app.schemas.auth import UserInfo
from app.schemas.comment import CommentInfo, CreateCommentRequest

router = APIRouter(tags=["评论"])


def _require_entry_member(entry_id: int, user: User, db: Session):
    entry = db.query(MoodEntry).filter(MoodEntry.id == entry_id).first()
    if not entry:
        raise NotFound("心情记录")

    exists = (
        db.query(CalendarMember)
        .filter(
            CalendarMember.calendar_id == entry.calendar_id,
            CalendarMember.user_id == user.id,
        )
        .first()
    )
    if not exists:
        raise NotMember()
    return entry


@router.get("/api/entries/{entry_id}/comments", response_model=dict)
def list_comments(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entry_member(entry_id, current_user, db)

    # 一次性 JOIN 查询用户，告别 N+1
    rows = (
        db.query(Comment, User)
        .join(User, Comment.user_id == User.id)
        .filter(Comment.entry_id == entry_id)
        .order_by(Comment.created_at)
        .all()
    )

    result = []
    for comment, user in rows:
        if not user:
            continue
        result.append(
            CommentInfo(
                id=comment.id,
                user=UserInfo(
                    id=user.id, nickname=user.nickname, avatar=user.avatar
                ),
                content=comment.content,
                is_mine=(comment.user_id == current_user.id),
                created_at=comment.created_at,
            )
        )

    return {"data": [r.model_dump() for r in result]}


@router.post(
    "/api/entries/{entry_id}/comments",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    entry_id: int,
    request: CreateCommentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entry_member(entry_id, current_user, db)

    comment = Comment(
        entry_id=entry_id,
        user_id=current_user.id,
        content=request.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "data": CommentInfo(
            id=comment.id,
            user=UserInfo(
                id=current_user.id,
                nickname=current_user.nickname,
                avatar=current_user.avatar,
            ),
            content=comment.content,
            is_mine=True,
            created_at=comment.created_at,
        ).model_dump()
    }


@router.delete(
    "/api/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise NotFound("评论")

    if comment.user_id != current_user.id:
        raise NotAuthorized("只能删除自己的评论")

    db.delete(comment)
    db.commit()
