from datetime import datetime

from pydantic import BaseModel, field_validator

from app.schemas.auth import UserInfo


class CommentInfo(BaseModel):
    id: int
    user: UserInfo
    content: str
    is_mine: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateCommentRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("评论内容不能为空")
        if len(v) > 200:
            raise ValueError("评论内容不能超过 200 字")
        return v
