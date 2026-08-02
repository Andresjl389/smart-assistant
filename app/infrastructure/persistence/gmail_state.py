import json
from pathlib import Path

from app.shared.config.settings import settings


class GmailState:
    def __init__(self):
        self.path = Path(settings.GMAIL_STATE_FILE)

    def get_history_id(self):
        if not self.path.exists():
            return None

        state = json.loads(self.path.read_text())
        return state.get("history_id")

    def save_history_id(self, history_id: str):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"history_id": history_id}))
