from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_member
from app.exceptions import (
    AlreadyMember,
    CalendarFull,
    CreatorCannotLeave,
    InvalidInviteCode,
    NotAuthorized,
    NotFound,
    SelfRemoveNotAllowed,
)
from app.models.calendar import Calendar, CalendarMember
from app.models.user import User
from app.schemas.calendar import (
    CalendarDetail,
    CalendarSummary,
    CreateCalendarRequest,
    JoinCalendarRequest,
    MemberInfo,
    UpdateCalendarRequest,
)
from app.utils.invite_code import generate_invite_code

router = APIRouter(prefix="/api/calendars", tags=["日历"])


def _get_calendar(calendar_id: int, db: Session) -> Calendar:
    cal = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not cal:
        raise NotFound("日历")
    return cal


def _require_creator(calendar: Calendar, user: User):
    if calendar.creator_id != user.id:
        raise NotAuthorized()


def _build_member_list(calendar_id: int, db: Session) -> list[MemberInfo]:
    """获取成员列表（1 次 JOIN 查询，告别 N+1）"""
    rows = (
        db.query(CalendarMember, User)
        .join(User, CalendarMember.user_id == User.id)
        .filter(CalendarMember.calendar_id == calendar_id)
        .all()
    )
    result = []
    for member, user in rows:
        result.append(
            MemberInfo(
                id=user.id,
                nickname=user.nickname,
                avatar=user.avatar,
                role=member.role,
                joined_at=member.joined_at,
            )
        )
    return result


def _build_calendar_detail(
    calendar: Calendar, user: User, db: Session
) -> CalendarDetail:
    return CalendarDetail(
        id=calendar.id,
        name=calendar.name,
        invite_code=calendar.invite_code,
        member_count=calendar.member_count,
        max_members=calendar.max_members,
        is_owner=(calendar.creator_id == user.id),
        members=_build_member_list(calendar.id, db),
        created_at=calendar.created_at,
    )


# ─── API 端点 ──────────────────────────────


@router.get("", response_model=dict)
def list_calendars(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memberships = (
        db.query(CalendarMember)
        .filter(CalendarMember.user_id == current_user.id)
        .all()
    )
    calendar_ids = [m.calendar_id for m in memberships]
    calendars = db.query(Calendar).filter(Calendar.id.in_(calendar_ids)).all()

    result = []
    for cal in calendars:
        members = _build_member_list(cal.id, db)
        result.append(
            CalendarSummary(
                id=cal.id,
                name=cal.name,
                member_count=cal.member_count,
                max_members=cal.max_members,
                members=members,
                is_owner=(cal.creator_id == current_user.id),
                created_at=cal.created_at,
            )
        )

    return {"data": [r.model_dump() for r in result]}


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_calendar(
    request: CreateCalendarRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invite_code = generate_invite_code()
    while db.query(Calendar).filter(Calendar.invite_code == invite_code).first():
        invite_code = generate_invite_code()

    calendar = Calendar(
        name=request.name,
        invite_code=invite_code,
        creator_id=current_user.id,
        member_count=1,
        max_members=4,
    )
    db.add(calendar)
    db.flush()

    member = CalendarMember(
        calendar_id=calendar.id,
        user_id=current_user.id,
        role="creator",
    )
    db.add(member)
    db.commit()
    db.refresh(calendar)

    detail = _build_calendar_detail(calendar, current_user, db)
    return {"data": detail.model_dump()}


@router.post("/join", response_model=dict)
def join_calendar(
    request: JoinCalendarRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    calendar = (
        db.query(Calendar)
        .filter(Calendar.invite_code == request.invite_code)
        .first()
    )
    if not calendar:
        raise InvalidInviteCode()

    existing = (
        db.query(CalendarMember)
        .filter(
            CalendarMember.calendar_id == calendar.id,
            CalendarMember.user_id == current_user.id,
        )
        .first()
    )
    if existing:
        raise AlreadyMember()

    if calendar.member_count >= calendar.max_members:
        raise CalendarFull()

    member = CalendarMember(
        calendar_id=calendar.id,
        user_id=current_user.id,
        role="member",
    )
    db.add(member)
    calendar.member_count += 1
    db.commit()

    detail = _build_calendar_detail(calendar, current_user, db)
    return {"data": detail.model_dump()}


@router.get("/{calendar_id}", response_model=dict)
def get_calendar(
    calendar_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    calendar = _get_calendar(calendar_id, db)
    require_member(calendar_id, current_user, db)
    detail = _build_calendar_detail(calendar, current_user, db)
    return {"data": detail.model_dump()}


@router.patch("/{calendar_id}", response_model=dict)
def update_calendar(
    calendar_id: int,
    request: UpdateCalendarRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    calendar = _get_calendar(calendar_id, db)
    _require_creator(calendar, current_user)

    if request.name is not None:
        calendar.name = request.name
    db.commit()
    db.refresh(calendar)

    detail = _build_calendar_detail(calendar, current_user, db)
    return {"data": detail.model_dump()}


@router.delete("/{calendar_id}", status_code=status.HTTP_204_NO_CONTENT)
def disband_calendar(
    calendar_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    calendar = _get_calendar(calendar_id, db)
    _require_creator(calendar, current_user)
    db.delete(calendar)
    db.commit()


@router.get("/{calendar_id}/members", response_model=dict)
def list_members(
    calendar_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_member(calendar_id, current_user, db)
    members = _build_member_list(calendar_id, db)
    return {"data": [m.model_dump() for m in members]}


@router.delete(
    "/{calendar_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_member(
    calendar_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    calendar = _get_calendar(calendar_id, db)
    _require_creator(calendar, current_user)

    if user_id == current_user.id:
        raise SelfRemoveNotAllowed()

    member = (
        db.query(CalendarMember)
        .filter(
            CalendarMember.calendar_id == calendar_id,
            CalendarMember.user_id == user_id,
        )
        .first()
    )
    if not member:
        raise NotFound("成员")

    db.delete(member)
    calendar.member_count -= 1
    db.commit()


@router.delete(
    "/{calendar_id}/leave",
    status_code=status.HTTP_204_NO_CONTENT,
)
def leave_calendar(
    calendar_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """成员主动退出日历"""
    calendar = _get_calendar(calendar_id, db)

    # 创建者不能退出，只能解散
    if calendar.creator_id == current_user.id:
        raise CreatorCannotLeave()

    member = (
        db.query(CalendarMember)
        .filter(
            CalendarMember.calendar_id == calendar_id,
            CalendarMember.user_id == current_user.id,
        )
        .first()
    )
    if not member:
        raise NotFound("成员")

    db.delete(member)
    calendar.member_count -= 1
    db.commit()
