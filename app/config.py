"""应用配置：从 .env / 环境变量读取。"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_dotenv(path: Path) -> None:
    """极简 .env 解析，避免额外依赖。"""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


_load_dotenv(BASE_DIR / ".env")


class Settings:
    # --- 基础 ---
    APP_NAME: str = "GRF Coach"
    HOST: str = os.getenv("GRF_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("GRF_PORT", "7788"))
    DEBUG: bool = os.getenv("GRF_DEBUG", "0") == "1"

    # --- 数据库 ---
    DB_PATH: Path = Path(os.getenv("GRF_DB", str(BASE_DIR / "grf.db")))

    # --- 安全 ---
    SECRET_KEY: str = os.getenv("GRF_SECRET_KEY", "")
    SESSION_COOKIE: str = "grf_session"
    SESSION_TTL_HOURS: int = int(os.getenv("GRF_SESSION_TTL_HOURS", "720"))  # 30 天
    ALLOW_REGISTER: bool = os.getenv("GRF_ALLOW_REGISTER", "1") == "1"

    # --- LLM ---
    LLM_PROVIDER: str = os.getenv("GRF_LLM_PROVIDER", "deepseek")
    LLM_API_KEY: str = os.getenv("GRF_LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("GRF_LLM_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL: str = os.getenv("GRF_LLM_MODEL", "deepseek-chat")
    LLM_VISION_MODEL: str = os.getenv("GRF_LLM_VISION_MODEL", "deepseek-flash")
    LLM_TIMEOUT: int = int(os.getenv("GRF_LLM_TIMEOUT", "120"))

    # --- 上传 ---
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    MEAL_IMG_DIR: Path = DATA_DIR / "meal_images"
    MAX_UPLOAD_MB: int = int(os.getenv("GRF_MAX_UPLOAD_MB", "256"))

    # --- WebAuthn / Passkey ---
    WEBAUTHN_RP_ID: str = os.getenv("GRF_WEBAUTHN_RP_ID", "")
    WEBAUTHN_RP_NAME: str = os.getenv("GRF_WEBAUTHN_RP_NAME", "GRF Coach")
    WEBAUTHN_ORIGIN: str = os.getenv("GRF_WEBAUTHN_ORIGIN", "")


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.MEAL_IMG_DIR.mkdir(parents=True, exist_ok=True)

if not settings.SECRET_KEY:
    import secrets

    settings.SECRET_KEY = secrets.token_urlsafe(48)