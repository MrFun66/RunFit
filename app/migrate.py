"""\u8f7b\u91cf\u8fc1\u79fb\uff1a\u4e3a\u5df2\u5b58\u5728\u7684 SQLite \u8868\u8865\u9f50\u65b0\u589e\u5217\u3002

SQLAlchemy \u7684 create_all \u53ea\u5efa\u65b0\u8868\uff0c\u4e0d\u4f1a ALTER \u5df2\u6709\u8868\u3002
\u8fd9\u91cc\u7528 PRAGMA \u68c0\u67e5 + ALTER TABLE \u8865\u9f50\uff0c\u4fdd\u8bc1\u5347\u7ea7\u4e0d\u7834\u574f\u65e7\u5e93\u3002
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

log = logging.getLogger("grf.migrate")

_WANTED: list[tuple[str, str, str]] = [
    ("users", "sync_token", "VARCHAR(96)"),
    ("users", "timezone", "VARCHAR(64)"),
    ("users", "onboarded", "BOOLEAN DEFAULT 0"),
    ("body_metrics", "sleep_hours", "FLOAT"),
    ("body_metrics", "muscle_kg", "FLOAT"),
    ("body_metrics", "source", "VARCHAR(32)"),
    ("runs", "avg_power", "FLOAT"),
    ("runs", "raw_meta", "TEXT"),
    ("coach_messages", "module", "VARCHAR(16)"),
    ("coach_messages", "context_json", "TEXT"),
]


def _columns(conn, table: str) -> set[str]:
    try:
        rows = conn.execute(text('PRAGMA table_info("%s")' % table)).fetchall()
    except Exception:
        return set()
    return {r[1] for r in rows}


def run_migrations(engine: Engine) -> list[str]:
    applied: list[str] = []
    with engine.begin() as conn:
        for table, col, ddl in _WANTED:
            cols = _columns(conn, table)
            if not cols:
                continue
            if col in cols:
                continue
            try:
                conn.execute(text('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (table, col, ddl)))
                applied.append("%s.%s" % (table, col))
                log.info("\u8fc1\u79fb\uff1a\u65b0\u589e\u5217 %s.%s", table, col)
            except Exception as exc:
                log.warning("\u8fc1\u79fb\u5931\u8d25 %s.%s: %s", table, col, exc)
    try:
        with engine.begin() as conn:
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_users_sync_token ON "users" ("sync_token")'))
    except Exception as exc:
        log.debug("\u7d22\u5f15\u521b\u5efa\u8df3\u8fc7: %s", exc)
    return applied