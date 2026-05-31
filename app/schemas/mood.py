from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.schemas.auth import UserInfo

ALLOWED_MOOD_TYPES = {"happy", "calm", "sad"}
MAX_IMAGES = 3


class MoodEntrySummary(BaseModel):
    id: int
    user: UserInfo
    date: date
    mood_type: str
    text: str = ""
    image_urls: list[str] = []
    created_at: datetime
    comment_count: int
    is_mine: bool = False

    model_config = {"from_attributes": True}


class MoodEntryDetail(BaseModel):
    id: int
    calendar_id: int
    user: UserInfo
    date: date
    mood_type: str
    text: str
    image_urls: list[str]
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_mine: bool = False

    model_config = {"from_attributes": True}


class CreateMoodEntryRequest(BaseModel):
    date: date
    mood_type: str
    text: Optional[str] = ""
    image_urls: Optional[list[str]] = None

    @field_validator("mood_type")
    @classmethod
    def mood_type_valid(cls, v: str) -> str:
        if v not in ALLOWED_MOOD_TYPES:
            raise ValueError(f"心情类型无效，仅支持 {ALLOWED_MOOD_TYPES}")
        return v

    @field_validator("text")
    @classmethod
    def text_length(cls, v: str | None) -> str | None:
        if v and len(v) > 500:
            raise ValueError("心情文字不能超过 500 字")
        return v

    @field_validator("image_urls")
    @classmethod
    def image_count(cls, v: list[str] | None) -> list[str] | None:
        if v and len(v) > MAX_IMAGES:
            raise ValueError(f"图片不能超过 {MAX_IMAGES} 张")
        return v


class MonthEntriesResponse(BaseModel):
    year: int
    month: int
    entries: list[MoodEntrySummary]


class RecentEntriesResponse(BaseModel):
    entries: list[MoodEntrySummary]


class HeatmapResponse(BaseModel):
    year: int
    days: dict[str, str]  # "2026-01-15" → "happy" | "calm" | "sad"
