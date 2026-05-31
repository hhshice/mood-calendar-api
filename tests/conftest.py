"""
测试配置与夹具

使用 SQLite 文件数据库，每个测试独立事务互不干扰。
"""
import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.utils.jwt import create_access_token

# 全局测试引擎（所有测试共用，但每个测试通过嵌套事务隔离）
TEST_DB_FILE = "test_mood_calendar.db"
TEST_ENGINE = create_engine(
    f"sqlite:///{TEST_DB_FILE}",
    connect_args={"check_same_thread": False},
)

# 创建全局会话工厂
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db() -> Generator[Session, None, None]:
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def global_setup():
    """整个测试会话开始时建表，结束后删表清文件"""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)
    TEST_ENGINE.dispose()
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


@pytest.fixture(autouse=True)
def clean_tables():
    """每个测试前清空所有表数据（保留表结构）"""
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()
    yield


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """提供数据库会话"""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """提供测试 HTTP 客户端"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_user(db: Session) -> User:
    """创建一个测试用户并返回"""
    user = User(openid="test_openid_001", nickname="测试用户", avatar="")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_token(test_user: User) -> str:
    """生成测试用户的 JWT Token"""
    return create_access_token(user_id=test_user.id)


@pytest.fixture
def auth_headers(user_token: str) -> dict:
    """提供 Authorization 请求头"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def another_user(db: Session) -> User:
    """创建另一个测试用户"""
    user = User(openid="test_openid_002", nickname="另一个用户", avatar="")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def another_token(another_user: User) -> str:
    return create_access_token(user_id=another_user.id)


@pytest.fixture
def another_headers(another_token: str) -> dict:
    return {"Authorization": f"Bearer {another_token}"}


def assert_error(response, expected_code: str, expected_status: int = 400):
    """验证错误响应格式"""
    assert response.status_code == expected_status
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == expected_code
    assert len(data["error"]["message"]) > 0
