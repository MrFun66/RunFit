"""按用户的 LLM 配置解析。

规则：
- 每个用户必须填自己的 API Key 才能用 AI。
- 唯一例外：站长（第一个注册的用户）可以使用 .env 里的全局 Key。
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from .config import settings
from .models import User, UserLlmConfig


@dataclass
class LlmCfg:
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    vision_model: str = "deepseek-flash"

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def owner_id(db: OrmSession) -> int | None:
    """站长 = id 最小的用户。只有 TA 能蹭 .env 里的全局 Key。"""
    return db.scalar(select(func.min(User.id)))


def is_owner(db: OrmSession, user: User | None) -> bool:
    if user is None:
        return False
    oid = owner_id(db)
    return oid is not None and user.id == oid


def get_cfg(db: OrmSession, user: User | None) -> LlmCfg:
    """用户自己的配置优先；站长没配时回退到 .env，其他人不回退。"""
    if user is not None:
        row = db.get(UserLlmConfig, user.id)
        if row and row.api_key:
            return LlmCfg(
                api_key=row.api_key,
                base_url=(row.base_url or settings.LLM_BASE_URL).rstrip("/"),
                model=row.model or settings.LLM_MODEL,
                vision_model=row.vision_model or settings.LLM_VISION_MODEL,
            )
        if is_owner(db, user) and settings.LLM_API_KEY:
            return LlmCfg(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL.rstrip("/"),
                model=settings.LLM_MODEL,
                vision_model=settings.LLM_VISION_MODEL,
            )
        return LlmCfg(api_key="", base_url=settings.LLM_BASE_URL.rstrip("/"),
                      model=settings.LLM_MODEL, vision_model=settings.LLM_VISION_MODEL)

    # 无用户上下文（后台任务）：允许全局
    return LlmCfg(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL.rstrip("/"),
        model=settings.LLM_MODEL,
        vision_model=settings.LLM_VISION_MODEL,
    )


def has_own_cfg(db: OrmSession, user: User) -> bool:
    row = db.get(UserLlmConfig, user.id)
    return bool(row and row.api_key)
