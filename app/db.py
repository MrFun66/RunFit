"""数据库连接与会话。"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

engine = create_engine(
    f"sqlite:///{settings.DB_PATH}",
    echo=settings.DEBUG,
    future=True,
    connect_args={"check_same_thread": False, "timeout": 30},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _record):  # noqa: ANN001
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_columns() -> None:
    """轻量迁移：给已有表补上后加的列（SQLite 的 ALTER TABLE ADD COLUMN）。"""
    from sqlalchemy import text

    wanted = {
        "users": {
            "sync_token": "VARCHAR(96)",
        },
    }
    with engine.begin() as conn:
        for table, cols in wanted.items():
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            have = {r[1] for r in rows}
            for col, ddl in cols.items():
                if col not in have:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))


def init_db() -> None:
    from . import models  # noqa: F401  确保模型注册

    Base.metadata.create_all(bind=engine)
    _ensure_columns()