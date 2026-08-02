from abc import ABC, abstractmethod


class EmailRepository(ABC):

    @abstractmethod
    async def get_recent_messages(self, max_results: int = 5):
        raise NotImplementedError

    @abstractmethod
    async def get_all_inbox_messages(self, max_messages: int | None = None):
        raise NotImplementedError

    @abstractmethod
    async def get_messages_since_history_id(self, history_id: str):
        raise NotImplementedError

    @abstractmethod
    async def get_current_history_id(self):
        raise NotImplementedError

    @abstractmethod
    async def apply_label(self, message_id: str, label_name: str):
        raise NotImplementedError

    @abstractmethod
    async def apply_labels(
        self,
        message_id: str,
        label_names: list[str],
        archive: bool = False,
    ):
        raise NotImplementedError

    @abstractmethod
    async def watch_mailbox(self, topic_name: str):
        raise NotImplementedError
