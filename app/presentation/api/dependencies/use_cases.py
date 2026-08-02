from fastapi import Depends

from app.application.use_cases.process_gmail_event import ProcessGmailEventUseCase
from app.domain.repositories.email_repository import EmailRepository
from app.presentation.api.dependencies.repositories import (
    get_email_repository,
)


def get_process_gmail_event_use_case(
    email_repository: EmailRepository = Depends(get_email_repository),
) -> ProcessGmailEventUseCase:
    return ProcessGmailEventUseCase(email_repository)