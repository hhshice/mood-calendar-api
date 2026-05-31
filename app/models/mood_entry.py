from sqlalchemy import (
    Column, Integer, String, Date, DateTime,
    ForeignKey, Text, JSON, UniqueConstraint, func,
)

from app.database import Base


class MoodEntry(Base):
    __tablename__ = "mood_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    calendar_id = Column(Integer, ForeignKey("calendars.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    mood_type = Column(String(16), nullable=False)
    text = Column(Text, default="")
    image_urls = Column(JSON, default=list)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("calendar_id", "user_id", "date", name="uq_mood_entry_per_day"),
    )
