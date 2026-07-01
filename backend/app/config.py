from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SOC_", env_file=".env", extra="ignore")

    # No SOC_ prefix on this one: it matches the Anthropic SDK's own
    # env var name, so `Anthropic()` (no args) and this Settings object
    # agree on where the key comes from.
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    model: str = "claude-opus-4-8"
    effort: str = "high"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
