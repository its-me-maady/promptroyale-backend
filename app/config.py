from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    PROJECT_NAME: str = "Prompt Royale API"
    VERSION: str = "0.1.0"
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/promptroyale.db"
    JWT_SECRET_KEY: str = "vaigai-college-prompt-royale-secret-key-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    GEMINI_API_KEY: str = ""

settings = Settings()
