from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

    PROJECT_NAME: str = "Prompt Royale API"
    VERSION: str = "0.1.0"
    DATABASE_URL: str | None = None
    JWT_SECRET_KEY: str = "vaigai-college-prompt-royale-secret-key-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    GEMINI_API_KEY: str = ""

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str | None) -> str:
        if not v or not v.strip():
            raise RuntimeError(
                "FATAL: DATABASE_URL is not set in environment or .env. Server execution halted."
            )
        return v.strip()


settings = Settings()
