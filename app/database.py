from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# 创建数据库引擎
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif "tidbcloud" in settings.database_url or "mysql" in settings.database_url:
    # TiDB Serverless 强制要求 TLS 连接
    import ssl
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    connect_args["ssl"] = ssl_ctx

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
