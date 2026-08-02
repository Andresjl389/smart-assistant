import base64
import json
import logging

from app.domain.repositories.email_repository import EmailRepository
from app.infrastructure.ai.email_classifier import EmailClassifier
from app.infrastructure.persistence.gmail_state import GmailState
from app.shared.config.settings import settings


logger = logging.getLogger(__name__)

class ProcessGmailEventUseCase:
    def __init__(
        self,
        email_repository: EmailRepository,
        classifier: EmailClassifier | None = None,
        gmail_state: GmailState | None = None,
    ):
        self.email_repository = email_repository
        self.classifier = classifier or EmailClassifier()
        self.gmail_state = gmail_state or GmailState()

    async def execute(self, payload: dict | None = None):
        if payload:
            return await self._process_gmail_event(payload)

        return await self.process_recent_messages()

    async def process_recent_messages(self):
        messages = await self.email_repository.get_recent_messages(
            max_results=settings.GMAIL_MAX_MESSAGES,
        )

        result = await self._organize_messages(messages)

        return {
            "received_payload": False,
            **result,
        }

    async def process_new_messages(self):
        previous_history_id = self.gmail_state.get_history_id()
        current_history_id = await self.email_repository.get_current_history_id()

        if not previous_history_id:
            self.gmail_state.save_history_id(current_history_id)

            return {
                "received_payload": False,
                "history_id": current_history_id,
                "organized": [],
                "message": "Primer historyId guardado. Ejecuta de nuevo cuando llegue otro correo.",
            }

        messages = await self.email_repository.get_messages_since_history_id(
            previous_history_id,
        )
        result = await self._organize_messages(messages)
        advanced = self._save_history_id_if_clean(current_history_id, result)

        return {
            "received_payload": False,
            "history_id": current_history_id,
            "history_id_advanced": advanced,
            **result,
        }

    async def process_all_inbox_messages(
        self,
        archive: bool = False,
        max_messages: int | None = None,
        max_new_classifications: int | None = None,
    ):
        messages = await self.email_repository.get_all_inbox_messages(
            max_messages=max_messages,
        )
        result = await self._organize_messages(
            messages,
            extra_labels=[settings.GMAIL_ALL_LABEL],
            archive=archive,
            max_new_classifications=(
                max_new_classifications
                if max_new_classifications is not None
                else settings.GMAIL_MAX_NEW_CLASSIFICATIONS
            ),
        )
        current_history_id = await self.email_repository.get_current_history_id()
        advanced = self._save_history_id_if_clean(current_history_id, result)

        return {
            "received_payload": False,
            "history_id": current_history_id,
            "history_id_advanced": advanced,
            "archive": archive,
            "all_label": settings.GMAIL_ALL_LABEL,
            **result,
        }

    async def watch_mailbox(self):
        response = await self.email_repository.watch_mailbox(
            topic_name=self._pubsub_topic_name(),
        )
        self.gmail_state.save_history_id(response["historyId"])

        return response

    async def _process_gmail_event(self, payload: dict):
        event = self._decode_pubsub_payload(payload)
        current_history_id = event["historyId"]
        previous_history_id = self.gmail_state.get_history_id()

        if not previous_history_id:
            self.gmail_state.save_history_id(current_history_id)

            return {
                "received_payload": True,
                "history_id": current_history_id,
                "organized": [],
                "message": "Primer historyId guardado. No habia estado previo para consultar cambios.",
            }

        messages = await self.email_repository.get_messages_since_history_id(
            previous_history_id,
        )
        result = await self._organize_messages(messages)
        advanced = self._save_history_id_if_clean(current_history_id, result)

        return {
            "received_payload": True,
            "history_id": current_history_id,
            "history_id_advanced": advanced,
            **result,
        }

    async def _organize_messages(
        self,
        messages: list[dict],
        extra_labels: list[str] | None = None,
        archive: bool = False,
        max_new_classifications: int | None = None,
    ):
        organized = []
        failed = []
        skipped = []
        decisions = []
        pending = []
        extra_labels = extra_labels or []

        for message in messages:
            existing_label = self._existing_ai_category(message)

            if existing_label:
                decisions.append(
                    {
                        "message": message,
                        "label": existing_label,
                        "reused": True,
                    }
                )
                continue

            if (
                max_new_classifications is not None
                and len(pending) >= max_new_classifications
            ):
                skipped.append(
                    {
                        "id": message["id"],
                        "subject": message["subject"],
                        "reason": "max_new_classifications_reached",
                    }
                )
                continue

            decision = {"message": message, "label": None, "reused": False}
            decisions.append(decision)
            pending.append(decision)

        if pending:
            try:
                labels = self.classifier.classify_batch(
                    [decision["message"] for decision in pending],
                )

                for decision, label_name in zip(pending, labels):
                    decision["label"] = label_name
            except Exception as error:
                logger.exception("Fallo la clasificacion en lote")

                for decision in pending:
                    decision["error"] = self._format_processing_error(error)

        for decision in decisions:
            message = decision["message"]

            if decision.get("error"):
                failed.append(
                    {
                        "id": message["id"],
                        "subject": message["subject"],
                        "error": decision["error"],
                    }
                )
                continue

            labels = [decision["label"], *extra_labels]

            try:
                await self.email_repository.apply_labels(
                    message["id"],
                    labels,
                    archive=archive,
                )
            except Exception as error:
                failed.append(
                    {
                        "id": message["id"],
                        "subject": message["subject"],
                        "error": self._format_processing_error(error),
                    }
                )
                continue

            organized.append(
                {
                    "id": message["id"],
                    "subject": message["subject"],
                    "label": decision["label"],
                    "labels": labels,
                    "archived": archive,
                    "skipped_classification": decision["reused"],
                }
            )

        return {
            "processed_count": len(organized),
            "failed_count": len(failed),
            "skipped_count": len(skipped),
            "organized": organized,
            "failed": failed,
            "skipped": skipped,
        }

    def _decode_pubsub_payload(self, payload: dict):
        data = payload["message"]["data"]
        padded_data = data + ("=" * (-len(data) % 4))
        decoded_data = base64.urlsafe_b64decode(padded_data)

        return json.loads(decoded_data)

    def _pubsub_topic_name(self):
        if settings.PUBSUB_TOPIC.startswith("projects/"):
            return settings.PUBSUB_TOPIC

        return f"projects/{settings.GOOGLE_PROJECT_ID}/topics/{settings.PUBSUB_TOPIC}"

    def _save_history_id_if_clean(self, history_id: str, result: dict) -> bool:
        if result["failed_count"]:
            logger.warning(
                "No se avanza el historyId: %s correos fallaron y se reintentaran.",
                result["failed_count"],
            )
            return False

        self.gmail_state.save_history_id(history_id)
        return True

    def _format_processing_error(self, error: Exception) -> str:
        error_text = str(error).replace("\n", " ")
        return error_text[:300]

    def _existing_ai_category(self, message: dict):
        category_labels = set(self.classifier.labels.values())

        for label_name in message.get("label_names", []):
            if label_name in category_labels:
                return label_name

        return None
