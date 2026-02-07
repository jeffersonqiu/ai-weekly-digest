"""Configuration loader using Pydantic Settings.

Why this approach:
- Loads from .env file automatically
- Type validation for all settings
- Cached via @lru_cache for performance
- Computed properties for dynamic values (like db_url)
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    postgres_user: str = "digest"
    postgres_password: str = "digest_secret"
    postgres_db: str = "weekly_digest"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None

    @property
    def db_url(self) -> str:
        """Build database URL from components or use DATABASE_URL if set."""
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # LLM Provider
    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # arXiv
    arxiv_categories: str = "cs.AI,cs.LG,cs.CL,cs.CV"
    arxiv_max_papers: int = 200
    arxiv_days_lookback: int = 7

    @property
    def arxiv_category_list(self) -> list[str]:
        """Parse comma-separated categories into a list."""
        return [cat.strip() for cat in self.arxiv_categories.split(",")]

    # Email (SMTP)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_pass: str | None = None
    email_to: str | None = None

    # Telegram
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Using @lru_cache ensures we only parse .env once.
    """
    return Settings()
