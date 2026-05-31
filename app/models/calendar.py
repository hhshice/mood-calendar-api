from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, SmallInteger,
    UniqueConstraint, func,
)

from app.database import Base


class Calendar(Base):
    __tablename__ = "calendars"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    invite_code = Column(String(8), unique=True, nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    member_count = Column(SmallInteger, nullable=False, default=1)
    max_members = Column(SmallInteger, nullable=False, default=4)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CalendarMember(Base):
    __tablename__ = "calendar_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    calendar_id = Column(Integer, ForeignKey("calendars.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(16), nullable=False, default="member")
    joined_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("calendar_id", "user_id", name="uq_calendar_member"),
    )
