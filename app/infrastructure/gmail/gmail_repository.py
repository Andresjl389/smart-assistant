import base64

from app.domain.repositories.email_repository import EmailRepository
from app.infrastructure.gmail.gmail_client import GmailClient


class GmailRepository(EmailRepository):

    def __init__(self):
        self.client = GmailClient().get_service()
        self._label_cache = None

    async def get_recent_messages(self, max_results: int = 5):
        response = (
            self.client.users()
            .messages()
            .list(
                userId="me",
                labelIds=["INBOX"],
                maxResults=max_results,
            )
            .execute()
        )

        messages = response.get("messages", [])
        return [self._get_message(message["id"]) for message in messages]

    async def get_all_inbox_messages(self, max_messages: int | None = None):
        message_ids = self._get_all_inbox_message_ids(max_messages)

        return [self._get_message(message_id) for message_id in message_ids]

    async def get_messages_since_history_id(self, history_id: str):
        message_ids = self._get_message_ids_from_history(history_id)
        messages = [self._get_message(message_id) for message_id in message_ids]

        return [
            message
            for message in messages
            if "INBOX" in message.get("label_ids", [])
        ]

    async def get_current_history_id(self):
        profile = (
            self.client.users()
            .getProfile(userId="me")
            .execute()
        )

        return profile["historyId"]

    async def apply_label(self, message_id: str, label_name: str):
        return await self.apply_labels(message_id, [label_name])

    async def apply_labels(
        self,
        message_id: str,
        label_names: list[str],
        archive: bool = False,
    ):
        label_ids = [
            self._get_or_create_label(label_name)
            for label_name in label_names
        ]
        remove_label_ids = ["INBOX"] if archive else []

        return (
            self.client.users()
            .messages()
            .modify(
                userId="me",
                id=message_id,
                body={
                    "addLabelIds": label_ids,
                    "removeLabelIds": remove_label_ids,
                },
            )
            .execute()
        )

    async def watch_mailbox(self, topic_name: str):
        return (
            self.client.users()
            .watch(
                userId="me",
                body={
                    "topicName": topic_name,
                    "labelIds": ["INBOX"],
                },
            )
            .execute()
        )

    def _get_all_inbox_message_ids(self, max_messages: int | None = None):
        message_ids = []
        page_token = None

        while True:
            remaining = None

            if max_messages is not None:
                remaining = max_messages - len(message_ids)

                if remaining <= 0:
                    return message_ids

            response = (
                self.client.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=["INBOX"],
                    maxResults=min(500, remaining or 500),
                    pageToken=page_token,
                )
                .execute()
            )

            message_ids.extend(
                message["id"]
                for message in response.get("messages", [])
            )

            page_token = response.get("nextPageToken")

            if not page_token:
                return message_ids

    def _get_message(self, message_id: str):
        message = (
            self.client.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="full",
            )
            .execute()
        )

        headers = {
            header["name"].lower(): header["value"]
            for header in message.get("payload", {}).get("headers", [])
        }

        return {
            "id": message["id"],
            "thread_id": message.get("threadId"),
            "history_id": message.get("historyId"),
            "label_ids": message.get("labelIds", []),
            "label_names": self._get_label_names(message.get("labelIds", [])),
            "from": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "snippet": message.get("snippet", ""),
            "body": self._extract_body(message.get("payload", {})),
        }

    def _get_label_names(self, label_ids: list[str]):
        label_cache = self._get_label_cache()
        labels_by_id = {
            label_id: label_name
            for label_name, label_id in label_cache.items()
        }

        return [
            labels_by_id.get(label_id, label_id)
            for label_id in label_ids
        ]

    def _get_message_ids_from_history(self, history_id: str):
        message_ids = []
        page_token = None

        while True:
            request = (
                self.client.users()
                .history()
                .list(
                    userId="me",
                    startHistoryId=history_id,
                    historyTypes=["messageAdded"],
                    labelId="INBOX",
                    pageToken=page_token,
                )
            )

            response = request.execute()

            for history in response.get("history", []):
                for added_message in history.get("messagesAdded", []):
                    message_id = added_message["message"]["id"]

                    if message_id not in message_ids:
                        message_ids.append(message_id)

            page_token = response.get("nextPageToken")

            if not page_token:
                return message_ids

    def _get_or_create_label(self, label_name: str):
        self._get_label_cache()

        if label_name in self._label_cache:
            return self._label_cache[label_name]

        label = (
            self.client.users()
            .labels()
            .create(
                userId="me",
                body={
                    "name": label_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            .execute()
        )

        self._label_cache[label_name] = label["id"]

        return label["id"]

    def _get_label_cache(self):
        if self._label_cache is None:
            labels_response = (
                self.client.users()
                .labels()
                .list(userId="me")
                .execute()
            )
            self._label_cache = {
                label["name"]: label["id"]
                for label in labels_response.get("labels", [])
            }

        return self._label_cache

    def _extract_body(self, payload: dict) -> str:
        data = self._find_plain_text_part(payload)

        if not data:
            return ""

        padded_data = data + ("=" * (-len(data) % 4))
        decoded = base64.urlsafe_b64decode(padded_data)
        return decoded.decode("utf-8", errors="replace")

    def _find_plain_text_part(self, payload: dict):
        body = payload.get("body", {})
        mime_type = payload.get("mimeType")

        if mime_type == "text/plain" and body.get("data"):
            return body["data"]

        for part in payload.get("parts", []):
            data = self._find_plain_text_part(part)
            if data:
                return data

        return None
