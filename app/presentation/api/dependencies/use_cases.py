from fastapi import Depends

from app.application.use_cases.manage_finance import ManageFinanceUseCase
from app.application.use_cases.process_gmail_event import ProcessGmailEventUseCase
from app.application.use_cases.track_work import TrackWorkUseCase
from app.domain.repositories.email_repository import EmailRepository
from app.domain.repositories.finance_repository import (
    AccountRepository,
    CategoryRepository,
    MovementRepository,
)
from app.domain.repositories.work_repository import WorkSessionRepository
from app.presentation.api.dependencies.repositories import (
    get_account_repository,
    get_category_repository,
    get_email_repository,
    get_movement_repository,
    get_work_session_repository,
)


def get_process_gmail_event_use_case(
    email_repository: EmailRepository = Depends(get_email_repository),
) -> ProcessGmailEventUseCase:
    return ProcessGmailEventUseCase(email_repository)


def get_manage_finance_use_case(
    movement_repository: MovementRepository = Depends(get_movement_repository),
    category_repository: CategoryRepository = Depends(get_category_repository),
    account_repository: AccountRepository = Depends(get_account_repository),
) -> ManageFinanceUseCase:
    return ManageFinanceUseCase(
        movement_repository,
        category_repository,
        account_repository,
    )


def get_track_work_use_case(
    work_session_repository: WorkSessionRepository = Depends(
        get_work_session_repository,
    ),
) -> TrackWorkUseCase:
    return TrackWorkUseCase(work_session_repository)
