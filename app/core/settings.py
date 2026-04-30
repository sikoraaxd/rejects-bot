from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    backend_url: str = Field(default="http://localhost:8000", description="Backend API URL.")

    sheet_url: str = Field(default="", description="Google Sheets URL.")
    google_service_account_file: str = Field(
        default="",
        description="Path to Google service account JSON file.",
    )
    llm_provider: str = Field(default="openai", description="LLM provider label.")
    llm_api_key: str = Field(default="", description="API key for OpenAI-compatible LLM.")
    llm_base_url: str = Field(default="", description="Optional OpenAI-compatible base URL.")
    llm_model: str = Field(
        default="gpt-4o-mini",
        description="LLM model name.",
    )

    qdrant_url: str = Field(default="http://localhost:6333", description="Qdrant URL.")
    qdrant_collection: str = Field(default="reject_cases", description="Qdrant collection name.")
    vector_size: int = Field(default=64, description="Dense vector size for hash embeddings.")

    cache_dir: str = Field(default="data/cache", description="Directory for local JSON cache.")

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cache_path(self) -> Path:
        return Path(self.cache_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
