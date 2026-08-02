from googleapiclient.discovery import build

from app.infrastructure.gmail.auth import authenticate


class GmailClient:

    def __init__(self):
        credentials = authenticate()
        self._service = build("gmail", "v1", credentials=credentials)

    @property
    def service(self):
        return self._service

    def get_service(self):
        return self._service
