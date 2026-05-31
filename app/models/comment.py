from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func

from app.database import Base


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(Integer, ForeignKey("mood_entries.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(String(200), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
