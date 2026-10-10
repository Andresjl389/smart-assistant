import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Depends, HTTPException, Response, status
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import APIKeyCookie

from app.infrastructure.persistence.database import session_scope
from app.infrastructure.persistence.models.auth import AuthSession, User
from app.shared.config.settings import settings

password_hash = PasswordHash.recommended()
session_cookie = APIKeyCookie(
    name=settings.AUTH_COOKIE_NAME,
    scheme_name="SessionCookie",
    auto_error=False,
)


async def get_current_user(token: str | None = Depends(session_cookie)) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inicia sesión.")
    async with session_scope() as session:
        record = await session.get(AuthSession, hashlib.sha256(token.encode()).hexdigest())
        if record is None or record.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o vencida.")
        user = await session.get(User, record.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida.")
        return user


async def create_session(session: AsyncSession, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(days=settings.AUTH_SESSION_DAYS)
    session.add(AuthSession(
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        user_id=user.id,
        expires_at=expires,
    ))
    response.set_cookie(
        settings.AUTH_COOKIE_NAME, token, httponly=True, secure=settings.AUTH_COOKIE_SECURE,
        samesite="lax", max_age=settings.AUTH_SESSION_DAYS * 86400, path="/",
    )


async def get_authenticated_user_id(user: User = Depends(get_current_user)) -> UUID:
    return user.id
