from fastapi import Depends
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.email_repository import EmailRepository
from app.domain.repositories.finance_repository import (
    AccountRepository,
    CategoryRepository,
    MovementRepository,
)
from app.domain.repositories.work_repository import (
    WorkPreferencesRepository,
    WorkSessionRepository,
)
from app.infrastructure.gmail.gmail_repository import GmailRepository
from app.infrastructure.persistence.repositories.sqlalchemy_finance_repository import (
    SqlAlchemyAccountRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyMovementRepository,
)
from app.infrastructure.persistence.repositories.sqlalchemy_work_repository import (
    SqlAlchemyWorkPreferencesRepository,
    SqlAlchemyWorkSessionRepository,
)
from app.presentation.api.dependencies.database import get_session
from app.presentation.api.dependencies.security import get_authenticated_user_id


def get_email_repository() -> EmailRepository:
    return GmailRepository()


def get_category_repository(
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_authenticated_user_id),
) -> CategoryRepository:
    return SqlAlchemyCategoryRepository(session, user_id)


def get_movement_repository(
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_authenticated_user_id),
) -> MovementRepository:
    return SqlAlchemyMovementRepository(session, user_id)


def get_work_session_repository(
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_authenticated_user_id),
) -> WorkSessionRepository:
    return SqlAlchemyWorkSessionRepository(session, user_id)


def get_work_preferences_repository(
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_authenticated_user_id),
) -> WorkPreferencesRepository:
    return SqlAlchemyWorkPreferencesRepository(session, user_id)


def get_account_repository(
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_authenticated_user_id),
) -> AccountRepository:
    return SqlAlchemyAccountRepository(session, user_id)
