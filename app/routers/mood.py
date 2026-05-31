from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_member
from app.exceptions import EntryAlreadyExists, NotAuthorized, NotFound
from app.models.calendar import CalendarMember
from app.models.comment import Comment
from app.models.mood_entry import MoodEntry
from app.models.user import User
from app.schemas.auth import UserInfo
from app.schemas.mood import (
    CreateMoodEntryRequest,
    MonthEntriesResponse,
    MoodEntryDetail,
    MoodEntrySummary,
    RecentEntriesResponse,
    HeatmapResponse,
)

router = APIRouter(tags=["心情记录"])


@router.get("/api/calendars/{calendar_id}/entries", response_model=dict)
def list_entries(
    calendar_id: int,
    year: int = Query(..., description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份（1-12）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_member(calendar_id, current_user, db)

    start_date = date(year, month, 1)
    end_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    # 一次性 JOIN 查询用户，告别 N+1
    entries = (
        db.query(MoodEntry, User)
        .join(User, MoodEntry.user_id == User.id)
        .filter(
            MoodEntry.calendar_id == calendar_id,
            MoodEntry.date >= start_date,
            MoodEntry.date < end_date,
        )
        .order_by(MoodEntry.date, MoodEntry.created_at)
        .all()
    )

    summary_list = []
    for entry, user in entries:
        comment_count = (
            db.query(Comment).filter(Comment.entry_id == entry.id).count()
        )
        summary_list.append(
            MoodEntrySummary(
                id=entry.id,
                user=UserInfo(id=user.id, nickname=user.nickname, avatar=user.avatar),
                date=entry.date,
                mood_type=entry.mood_type,
                text=entry.text or "",
                image_urls=entry.image_urls or [],
                created_at=entry.created_at,
                comment_count=comment_count,
                is_mine=(entry.user_id == current_user.id),
            )
        )

    return {
        "data": MonthEntriesResponse(
            year=year, month=month, entries=summary_list
        ).model_dump()
    }


@router.post(
    "/api/calendars/{calendar_id}/entries",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
def create_entry(
    calendar_id: int,
    request: CreateMoodEntryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_member(calendar_id, current_user, db)

    existing = (
        db.query(MoodEntry)
        .filter(
            MoodEntry.calendar_id == calendar_id,
            MoodEntry.user_id == current_user.id,
            MoodEntry.date == request.date,
        )
        .first()
    )
    if existing:
        raise EntryAlreadyExists()

    entry = MoodEntry(
        calendar_id=calendar_id,
        user_id=current_user.id,
        date=request.date,
        mood_type=request.mood_type,
        text=request.text or "",
        image_urls=request.image_urls or [],
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "data": MoodEntryDetail(
            id=entry.id,
            calendar_id=entry.calendar_id,
            user=UserInfo(
                id=current_user.id,
                nickname=current_user.nickname,
                avatar=current_user.avatar,
            ),
            date=entry.date,
            mood_type=entry.mood_type,
            text=entry.text,
            image_urls=entry.image_urls,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            is_mine=True,
        ).model_dump()
    }


@router.get("/api/entries/recent", response_model=dict)
def get_recent_entries(
    limit: int = Query(default=5, ge=1, le=20, description="返回条数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户所有日历中的最近心情记录（首页快照用）"""
    calendar_ids = [
        row[0]
        for row in db.query(CalendarMember.calendar_id)
        .filter(CalendarMember.user_id == current_user.id)
        .all()
    ]

    if not calendar_ids:
        return {"data": RecentEntriesResponse(entries=[]).model_dump()}

    entries = (
        db.query(MoodEntry, User)
        .join(User, MoodEntry.user_id == User.id)
        .filter(MoodEntry.calendar_id.in_(calendar_ids))
        .order_by(MoodEntry.created_at.desc())
        .limit(limit)
        .all()
    )

    summary_list = []
    for entry, user in entries:
        comment_count = (
            db.query(Comment).filter(Comment.entry_id == entry.id).count()
        )
        summary_list.append(
            MoodEntrySummary(
                id=entry.id,
                user=UserInfo(id=user.id, nickname=user.nickname, avatar=user.avatar),
                date=entry.date,
                mood_type=entry.mood_type,
                text=entry.text or "",
                image_urls=entry.image_urls or [],
                created_at=entry.created_at,
                comment_count=comment_count,
                is_mine=(entry.user_id == current_user.id),
            )
        )

    return {
        "data": RecentEntriesResponse(entries=summary_list).model_dump()
    }


@router.get("/api/entries/{entry_id}", response_model=dict)
def get_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(MoodEntry).filter(MoodEntry.id == entry_id).first()
    if not entry:
        raise NotFound("心情记录")

    require_member(entry.calendar_id, current_user, db)

    user = db.query(User).filter(User.id == entry.user_id).first()
    if not user:
        raise NotFound("用户")

    return {
        "data": MoodEntryDetail(
            id=entry.id,
            calendar_id=entry.calendar_id,
            user=UserInfo(
                id=user.id,
                nickname=user.nickname,
                avatar=user.avatar,
            ),
            date=entry.date,
            mood_type=entry.mood_type,
            text=entry.text,
            image_urls=entry.image_urls,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            is_mine=(entry.user_id == current_user.id),
        ).model_dump()
    }


@router.get("/api/calendars/{calendar_id}/stats/heatmap", response_model=dict)
def get_heatmap(
    calendar_id: int,
    year: int = Query(..., description="年份"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取某年心情热力图数据（GitHub commit 风格）"""
    require_member(calendar_id, current_user, db)

    result = _build_heatmap(calendar_id, year, current_user, db)
    return {"data": HeatmapResponse(year=result["year"], days=result["days"]).model_dump()}


@router.get("/api/stats/heatmap", response_model=dict)
def get_all_heatmap(
    year: int = Query(..., description="年份"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户所有日历合并的心情热力图"""
    calendar_ids = [
        row[0]
        for row in db.query(CalendarMember.calendar_id)
        .filter(CalendarMember.user_id == current_user.id)
        .all()
    ]
    if not calendar_ids:
        return {"data": HeatmapResponse(year=year, days={}).model_dump()}

    # 合并所有日历的数据
    all_days: dict[str, str] = {}
    for cid in calendar_ids:
        result = _build_heatmap(cid, year, current_user, db)
        for d, mood in result["days"].items():
            if d not in all_days:
                all_days[d] = mood

    return {"data": HeatmapResponse(year=year, days=all_days).model_dump()}


def _build_heatmap(calendar_id: int, year: int, current_user: User, db: Session) -> dict:
    start_date = date(year, 1, 1)
    end_date = date(year + 1, 1, 1)

    # 只查当前用户的心情记录
    entries = (
        db.query(MoodEntry)
        .filter(
            MoodEntry.calendar_id == calendar_id,
            MoodEntry.user_id == current_user.id,
            MoodEntry.date >= start_date,
            MoodEntry.date < end_date,
        )
        .all()
    )

    days: dict[str, str] = {}
    for e in entries:
        days[e.date.isoformat()] = e.mood_type

    return {"year": year, "days": days}


@router.delete("/api/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(MoodEntry).filter(MoodEntry.id == entry_id).first()
    if not entry:
        raise NotFound("心情记录")

    if entry.user_id != current_user.id:
        raise NotAuthorized("只能删除自己的心情记录")

    db.delete(entry)
    db.commit()
