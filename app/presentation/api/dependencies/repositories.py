from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.email_repository import EmailRepository
from app.domain.repositories.finance_repository import (
    AccountRepository,
    CategoryRepository,
    MovementRepository,
)
from app.domain.repositories.work_repository import WorkSessionRepository
from app.infrastructure.gmail.gmail_repository import GmailRepository
from app.infrastructure.persistence.repositories.sqlalchemy_finance_repository import (
    SqlAlchemyAccountRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyMovementRepository,
)
from app.infrastructure.persistence.repositories.sqlalchemy_work_repository import (
    SqlAlchemyWorkSessionRepository,
)
from app.presentation.api.dependencies.database import get_session


def get_email_repository() -> EmailRepository:
    return GmailRepository()


def get_category_repository(
    session: AsyncSession = Depends(get_session),
) -> CategoryRepository:
    return SqlAlchemyCategoryRepository(session)


def get_movement_repository(
    session: AsyncSession = Depends(get_session),
) -> MovementRepository:
    return SqlAlchemyMovementRepository(session)


def get_work_session_repository(
    session: AsyncSession = Depends(get_session),
) -> WorkSessionRepository:
    return SqlAlchemyWorkSessionRepository(session)


def get_account_repository(
    session: AsyncSession = Depends(get_session),
) -> AccountRepository:
    return SqlAlchemyAccountRepository(session)
