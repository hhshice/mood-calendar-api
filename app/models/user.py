from sqlalchemy import Column, Integer, String, DateTime, func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    openid = Column(String(64), unique=True, nullable=False, index=True)
    nickname = Column(String(64), nullable=False, default="")
    avatar = Column(String(512), nullable=False, default="")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
