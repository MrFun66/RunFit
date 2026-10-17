"""认证与密码。"""
from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from .config import settings
from .db import get_db
from .models import Session, User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_session(db: OrmSession, user: User) -> Session:
    token = secrets.token_urlsafe(48)
    exp = datetime.utcnow() + timedelta(hours=settings.SESSION_TTL_HOURS)
    sess = Session(token=token, user_id=user.id, expires_at=exp)
    db.add(sess)
    db.commit()
    return sess


def _token_from_request(request: Request) -> str | None:
    tok = request.cookies.get(settings.SESSION_COOKIE)
    if tok:
        return tok
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def current_user(request: Request, db: OrmSession = Depends(get_db)) -> User:
    token = _token_from_request(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    sess = db.get(Session, token)
    if not sess or sess.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期")
    user = db.get(User, sess.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def optional_user(request: Request, db: OrmSession = Depends(get_db)) -> User | None:
    try:
        return current_user(request, db)
    except HTTPException:
        return None


def first_user(db: OrmSession) -> User | None:
    return db.scalars(select(User).order_by(User.id)).first()