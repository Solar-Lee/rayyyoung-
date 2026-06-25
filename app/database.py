"""SQLModel engine / session 管理。"""
from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import DATABASE_URL

# SQLite + 多執行緒（uvicorn）需 check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    """建立所有資料表（若不存在）。"""
    import app.models  # noqa: F401  確保 model 已 import 註冊

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI 相依注入用的 session 產生器。"""
    with Session(engine) as session:
        yield session
