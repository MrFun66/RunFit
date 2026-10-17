"""WebAuthn / Passkey 认证。

设计要点：
- rp_id / origin 从请求 Host 动态推导，同时兼容 127.0.0.1 与 runfit.wenhh.top
- challenge 存在内存 dict（进程内），5 分钟过期
- 凭证公钥以 base64 存库
"""
from __future__ import annotations

import base64
import json
import secrets
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as OrmSession
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import options_to_json
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from .config import settings
from .db import get_db
from .models import User, WebauthnCredential
from .security import create_session, current_user, first_user

router = APIRouter(prefix="/api/auth/passkey")

# challenge 暂存：token -> (challenge_bytes, user_id|None, expires_at)
_CHALLENGES: dict[str, tuple[bytes, int | None, float]] = {}
_TTL = 300.0


def _gc() -> None:
    now = time.time()
    for k in [k for k, v in _CHALLENGES.items() if v[2] < now]:
        _CHALLENGES.pop(k, None)


def _put(challenge: bytes, user_id: int | None) -> str:
    _gc()
    tok = secrets.token_urlsafe(24)
    _CHALLENGES[tok] = (challenge, user_id, time.time() + _TTL)
    return tok


def _pop(tok: str) -> tuple[bytes, int | None]:
    item = _CHALLENGES.pop(tok, None)
    if not item:
        raise HTTPException(400, "challenge 已失效，请重新发起")
    challenge, uid, exp = item
    if exp < time.time():
        raise HTTPException(400, "challenge 已过期，请重新发起")
    return challenge, uid


def _rp(request: Request) -> tuple[str, str]:
    """返回 (rp_id, origin)。优先用配置，否则从请求推导。"""
    if settings.WEBAUTHN_RP_ID and settings.WEBAUTHN_ORIGIN:
        return settings.WEBAUTHN_RP_ID, settings.WEBAUTHN_ORIGIN
    host = request.headers.get("host", "127.0.0.1:7788")
    hostname = host.split(":")[0]
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "http"
    origin = f"{proto}://{host}"
    return hostname, origin


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


# ---------------------------------------------------------------------------
# 注册（已登录用户绑定一个 passkey）
# ---------------------------------------------------------------------------
@router.post("/register/begin")
def register_begin(
    request: Request,
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    rp_id, _ = _rp(request)
    existing = db.scalars(
        select(WebauthnCredential).where(WebauthnCredential.user_id == user.id)
    ).all()
    exclude = [
        PublicKeyCredentialDescriptor(id=_b64d(c.credential_id)) for c in existing
    ]
    opts = generate_registration_options(
        rp_id=rp_id,
        rp_name=settings.WEBAUTHN_RP_NAME,
        user_id=str(user.id).encode(),
        user_name=user.username,
        user_display_name=user.username,
        exclude_credentials=exclude or None,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    tok = _put(opts.challenge, user.id)
    return {"challenge_token": tok, "options": json.loads(options_to_json(opts))}


class RegFinishIn(BaseModel):
    challenge_token: str
    credential: dict
    name: str | None = None


@router.post("/register/finish")
def register_finish(
    body: RegFinishIn,
    request: Request,
    user: User = Depends(current_user),
    db: OrmSession = Depends(get_db),
):
    challenge, uid = _pop(body.challenge_token)
    if uid != user.id:
        raise HTTPException(400, "用户不匹配")
    rp_id, origin = _rp(request)
    try:
        v = verify_registration_response(
            credential=body.credential,
            expected_challenge=challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"验证失败：{exc}") from exc

    cred_id = _b64e(v.credential_id)
    if db.scalars(
        select(WebauthnCredential).where(WebauthnCredential.credential_id == cred_id)
    ).first():
        raise HTTPException(400, "该设备已绑定")

    row = WebauthnCredential(
        user_id=user.id,
        credential_id=cred_id,
        public_key=_b64e(v.credential_public_key),
        sign_count=v.sign_count,
        transports=json.dumps(body.credential.get("response", {}).get("transports") or []),
        name=body.name or "我的设备",
    )
    db.add(row)
    db.commit()
    return {"ok": True, "id": row.id, "name": row.name}


# ---------------------------------------------------------------------------
# 登录（无需密码）
# ---------------------------------------------------------------------------
class LoginBeginIn(BaseModel):
    username: str | None = None


@router.post("/login/begin")
def login_begin(body: LoginBeginIn, request: Request, db: OrmSession = Depends(get_db)):
    rp_id, _ = _rp(request)
    allow = None
    uid: int | None = None
    if body.username:
        u = db.scalars(select(User).where(User.username == body.username)).first()
        if u:
            uid = u.id
            creds = db.scalars(
                select(WebauthnCredential).where(WebauthnCredential.user_id == u.id)
            ).all()
            if not creds:
                raise HTTPException(404, "该用户还没有绑定 passkey")
            allow = [
                PublicKeyCredentialDescriptor(id=_b64d(c.credential_id)) for c in creds
            ]
    opts = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=allow,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    tok = _put(opts.challenge, uid)
    return {"challenge_token": tok, "options": json.loads(options_to_json(opts))}


class LoginFinishIn(BaseModel):
    challenge_token: str
    credential: dict


@router.post("/login/finish")
def login_finish(
    body: LoginFinishIn,
    request: Request,
    response: Response,
    db: OrmSession = Depends(get_db),
):
    challenge, _uid = _pop(body.challenge_token)
    cred_id = body.credential.get("id") or body.credential.get("rawId")
    if not cred_id:
        raise HTTPException(400, "缺少凭证 id")

    row = db.scalars(
        select(WebauthnCredential).where(WebauthnCredential.credential_id == cred_id)
    ).first()
    if not row:
        raise HTTPException(404, "未找到该 passkey，请先用密码登录并绑定")

    rp_id, origin = _rp(request)
    try:
        v = verify_authentication_response(
            credential=body.credential,
            expected_challenge=challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=_b64d(row.public_key),
            credential_current_sign_count=row.sign_count,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"验证失败：{exc}") from exc

    row.sign_count = v.new_sign_count
    row.last_used_at = datetime.utcnow()
    db.commit()

    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(404, "用户不存在")

    sess = create_session(db, user)
    response.set_cookie(
        settings.SESSION_COOKIE,
        sess.token,
        httponly=True,
        samesite="lax",
        max_age=settings.SESSION_TTL_HOURS * 3600,
        secure=origin.startswith("https"),
    )
    return {"ok": True, "username": user.username}


# ---------------------------------------------------------------------------
# 管理
# ---------------------------------------------------------------------------
@router.get("/list")
def list_passkeys(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    rows = db.scalars(
        select(WebauthnCredential)
        .where(WebauthnCredential.user_id == user.id)
        .order_by(WebauthnCredential.id)
    ).all()
    return {
        "items": [
            {
                "id": r.id,
                "name": r.name,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "last_used_at": r.last_used_at.isoformat() if r.last_used_at else None,
            }
            for r in rows
        ]
    }


@router.delete("/{cid:int}")
def delete_passkey(
    cid: int, user: User = Depends(current_user), db: OrmSession = Depends(get_db)
):
    row = db.get(WebauthnCredential, cid)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/available")
def available(request: Request, db: OrmSession = Depends(get_db)):
    """告诉前端：是否可用、是否有已绑定用户。"""
    rp_id, origin = _rp(request)
    total = db.scalar(select(func.count()).select_from(WebauthnCredential)) or 0
    return {
        "enabled": True,
        "rp_id": rp_id,
        "origin": origin,
        "credential_count": total,
        "has_users": first_user(db) is not None,
    }