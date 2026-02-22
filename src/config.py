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

    # Environment mode: "test" or "prod"
    app_env: str = "test"

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
    arxiv_max_papers: int = 10000  # Effectively unlimited - fetch all available papers
    arxiv_days_lookback: int = 7
    priority_authors: str = "Turing,Hinton,LeCun,Bengio,Sutskever"

    @property
    def priority_author_list(self) -> list[str]:
        """Parse comma-separated authors into a list."""
        return [auth.strip().lower() for auth in self.priority_authors.split(",")]

    @property
    def arxiv_category_list(self) -> list[str]:
        """Parse comma-separated categories into a list."""
        return [cat.strip() for cat in self.arxiv_categories.split(",")]

    # Email (SMTP)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_pass: str | None = None
    email_to_test: str | None = None
    email_to_prod: str | None = None

    @property
    def email_to_list(self) -> list[str]:
        """Parse comma-separated email addresses into a list based on environment."""
        target = self.email_to_prod if self.app_env == "prod" else self.email_to_test
        if not target:
            return []
        return [email.strip() for email in target.split(",") if email.strip()]

    # Telegram
    telegram_bot_token: str | None = None
    telegram_chat_id_test: str | None = None
    telegram_chat_id_prod: str | None = None

    @property
    def telegram_chat_id(self) -> str | None:
        """Get the correct Telegram chat ID based on environment."""
        return self.telegram_chat_id_prod if self.app_env == "prod" else self.telegram_chat_id_test


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Using @lru_cache ensures we only parse .env once.
    """
    return Settings()
