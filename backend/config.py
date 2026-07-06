import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Explicitly load .env using python-dotenv as requested
load_dotenv()

class Settings(BaseSettings):
    app_version: str = "1.0.0"
    api_key: str
    duckdb_path: str = "./data/shipforesight.db"
    models_dir: str = "./models"
    groq_api_key: str
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    host: str = "0.0.0.0"
    port: int = 8000
    explain_ttl_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

@lru_cache()
def get_settings() -> Settings:
    """
    Validates at startup that all required environment variables exist.
    Raises a clear error if required keys (like API_KEY or GROQ_API_KEY) are missing.
    """
    try:
        return Settings()
    except Exception as e:
        raise ValueError(f"Startup Error: Missing or invalid environment variables. Details:\n{e}")
