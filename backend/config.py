from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    github_token: str = ""
    youtube_api_key: str = ""

    database_url: str = "sqlite:///./app.db"

    max_upload_size_mb: int = 10
    max_provider_resumes: int = 25

    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    demo_mode: bool = True

    @property
    def frontend_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def ai_available(self) -> bool:
        return bool(self.groq_api_key) and not self.demo_mode


@lru_cache
def get_settings() -> Settings:
    return Settings()
