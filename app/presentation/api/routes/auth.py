import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.presentation.api.dependencies.database import get_session
from app.infrastructure.persistence.models.auth import AuthSession, User
from app.presentation.api.dependencies.security import (
    create_session, get_current_user, password_hash,
)
from app.shared.config.settings import settings

router = APIRouter(prefix="/auth", tags=["Autenticación"])


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserDTO(BaseModel):
    id: UUID
    email: str


@router.post("/register", response_model=UserDTO, status_code=status.HTTP_201_CREATED)
async def register(data: Credentials, response: Response, session: AsyncSession = Depends(get_session)):
    email = str(data.email).lower()
    existing = await session.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="Ese correo ya está registrado.")
    user = User(email=email, password_hash=password_hash.hash(data.password))
    session.add(user)
    await session.flush()
    legacy = await session.scalar(select(User).where(User.email == "legacy-data@internal.invalid"))
    if legacy is not None:
        from app.infrastructure.persistence.models.finance.account import Account
        from app.infrastructure.persistence.models.finance.category import Category
        from app.infrastructure.persistence.models.finance.movement import Movement
        from app.infrastructure.persistence.models.work.work_session import WorkSession
        for model in (Account, Category, Movement, WorkSession):
            rows = await session.scalars(select(model).where(model.user_id == legacy.id))
            for row in rows:
                row.user_id = user.id
        await session.delete(legacy)
        await session.flush()
    await create_session(session, user, response)
    return UserDTO(id=user.id, email=user.email)


@router.post("/login", response_model=UserDTO)
async def login(data: Credentials, response: Response, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(User.email == str(data.email).lower()))
    if user is None or not password_hash.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")
    await create_session(session, user, response)
    return UserDTO(id=user.id, email=user.email)


@router.get("/me", response_model=UserDTO)
async def me(user: User = Depends(get_current_user)):
    return UserDTO(id=user.id, email=user.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    token = request.cookies.get(settings.AUTH_COOKIE_NAME, "")
    record = await session.get(AuthSession, hashlib.sha256(token.encode()).hexdigest())
    if record is not None:
        await session.delete(record)
    response.delete_cookie(settings.AUTH_COOKIE_NAME, path="/", httponly=True, secure=settings.AUTH_COOKIE_SECURE, samesite="lax")
    return None
