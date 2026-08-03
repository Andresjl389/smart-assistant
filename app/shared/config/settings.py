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
    DATABASE_URL: str = "sqlite+aiosqlite:///.data/smart_assistant.db"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 1800
    CORS_ORIGINS: str = "*"
    CORS_ALLOW_CREDENTIALS: bool = False
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"
    CORS_MAX_AGE: int = 600

    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore'
    )

    @property
    def cors_origins(self) -> list[str]:
        return self._split(self.CORS_ORIGINS)

    @property
    def cors_allow_methods(self) -> list[str]:
        return self._split(self.CORS_ALLOW_METHODS)

    @property
    def cors_allow_headers(self) -> list[str]:
        return self._split(self.CORS_ALLOW_HEADERS)

    @staticmethod
    def _split(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

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
