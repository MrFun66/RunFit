"""GRF Coach — 应用入口。

启动：python -m app.main   或   uvicorn app.main:app --host 0.0.0.0 --port 7788
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .config import BASE_DIR, settings
from .db import engine, init_db
from .migrate import run_migrations
from .sync_api import router as sync_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
log = logging.getLogger("grf")

STATIC_DIR = BASE_DIR / "web"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    _applied = run_migrations(engine)
    if _applied:
        log.info('schema migration: %s', ', '.join(_applied))
    # 内置动作库 + 三分化模板（幂等，已有则跳过）
    from .db import SessionLocal
    from .exercises_seed import seed_exercises
    from .templates_seed import seed_templates

    with SessionLocal() as _db:
        n_ex = seed_exercises(_db)
        n_tp = seed_templates(_db)
        if n_ex or n_tp:
            log.info("种子数据写入: 动作 %s 个, 模板 %s 套", n_ex, n_tp)
    log.info("数据库就绪: %s", settings.DB_PATH)
    log.info("LLM 配置: %s", "已配置" if settings.LLM_API_KEY else "未配置（教练对话不可用）")
    log.info("监听: http://%s:%s", settings.HOST, settings.PORT)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="营养师 + 跑步数据分析师 + 力量教练 三合一",
    version="1.0.0",
    lifespan=lifespan,
)

# 本地/穿透访问都放行；认证靠 Cookie + 强密码，不依赖 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(sync_router)

from .webauthn_auth import router as passkey_router  # noqa: E402
app.include_router(passkey_router)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "app": settings.APP_NAME,
        "llm_configured": bool(settings.LLM_API_KEY),
    }


@app.exception_handler(Exception)
async def _unhandled(_request: Request, exc: Exception):
    log.exception("未处理异常: %s", exc)
    return JSONResponse(status_code=500, content={"detail": f"服务器内部错误: {exc}"})


# --- 静态前端 ---
if STATIC_DIR.exists():
    class NoCacheStatic(StaticFiles):
        async def get_response(self, path, scope):
            resp = await super().get_response(path, scope)
            resp.headers["Cache-Control"] = "no-cache, must-revalidate"
            return resp

    app.mount("/assets", NoCacheStatic(directory=STATIC_DIR / "assets"), name="assets")

    NOCACHE = {"Cache-Control": "no-cache, must-revalidate", "Pragma": "no-cache"}

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html", headers=NOCACHE)

    @app.get("/favicon.ico")
    def favicon():
        p = STATIC_DIR / "favicon.ico"
        if p.exists():
            return FileResponse(p)
        p2 = STATIC_DIR / "assets" / "icon-192.png"
        if p2.exists():
            return FileResponse(p2)
        return JSONResponse(status_code=204, content=None)

    @app.get("/manifest.json")
    def manifest():
        p = STATIC_DIR / "manifest.json"
        if p.exists():
            return FileResponse(p, media_type="application/manifest+json")
        return JSONResponse(status_code=404, content={"detail": "not found"})

    @app.get("/sw.js")
    def service_worker():
        p = STATIC_DIR / "sw.js"
        if p.exists():
            # Service Worker 绝不能被缓存，否则旧 SW 会一直供给旧页面
            return FileResponse(
                p,
                media_type="application/javascript",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )
        return JSONResponse(status_code=404, content={"detail": "not found"})
else:
    log.warning("前端目录不存在: %s", STATIC_DIR)


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )


if __name__ == "__main__":
    run()