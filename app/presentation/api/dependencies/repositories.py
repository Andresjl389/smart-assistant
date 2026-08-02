from app.infrastructure.gmail.gmail_repository import GmailRepository
from app.domain.repositories.email_repository import EmailRepository


def get_email_repository() -> EmailRepository:
    return GmailRepository()