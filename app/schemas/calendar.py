from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.schemas.auth import UserInfo


class MemberInfo(BaseModel):
    id: int
    nickname: str
    avatar: str
    role: str  # 'creator' | 'member'
    joined_at: datetime

    model_config = {"from_attributes": True}


class CalendarSummary(BaseModel):
    id: int
    name: str
    member_count: int
    max_members: int
    members: list[MemberInfo]
    is_owner: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CalendarDetail(BaseModel):
    id: int
    name: str
    invite_code: str
    member_count: int
    max_members: int
    is_owner: bool
    members: list[MemberInfo]
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateCalendarRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("日历名称不能为空")
        if len(v) > 10:
            raise ValueError("日历名称不能超过 10 个字")
        return v


class JoinCalendarRequest(BaseModel):
    invite_code: str

    @field_validator("invite_code")
    @classmethod
    def code_valid(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) != 6:
            raise ValueError("邀请码必须为 6 位")
        if not v.isalnum():
            raise ValueError("邀请码只能包含字母和数字")
        return v


class UpdateCalendarRequest(BaseModel):
    name: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("日历名称不能为空")
            if len(v) > 10:
                raise ValueError("日历名称不能超过 10 个字")
        return v
