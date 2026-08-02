from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Smart Assistant"
    APP_VERSION: str = '0.1.0'

    API_KEY: str
    AI_PROVIDER: str = "openrouter"
    AI_BATCH_SIZE: int = 20
    AI_RULES_PREFILTER: bool = True
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-flash-latest"
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str = "openrouter/free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_SITE_URL: str | None = None
    OPENROUTER_SITE_NAME: str = "Smart Assistant"
    GMAIL_MAX_MESSAGES: int = 5
    GMAIL_MAX_NEW_CLASSIFICATIONS: int = 5
    GMAIL_ALL_LABEL: str = "AI/Todos"
    GOOGLE_PROJECT_ID: str
    PUBSUB_TOPIC: str
    GMAIL_STATE_FILE: str = ".data/gmail_state.json"

    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore'
    )

    @property
    def gemini_api_key(self) -> str:
        return self.GEMINI_API_KEY or self.API_KEY

    @property
    def openrouter_api_key(self) -> str:
        return self.OPENROUTER_API_KEY or self.API_KEY

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
