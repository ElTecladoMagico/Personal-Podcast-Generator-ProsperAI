from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

CommaList = Annotated[list[str], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str
    openai_api_key: str = ""
    elevenlabs_api_key: str = ""
    guardian_api_key: str = "test"
    clerk_issuer: str
    clerk_authorized_parties: CommaList = []
    cors_origins: CommaList = []
    public_base_url: str = "http://localhost:8000"
    audio_dir: str = "./data/audio"
    scheduler_enabled: bool = True
    max_concurrent_generations: int = 3
    episode_max_minutes: int = 2
    max_manual_episodes_per_day: int = 5

    @field_validator("clerk_authorized_parties", "cors_origins", mode="before")
    @classmethod
    def split_commas(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


settings = Settings()
