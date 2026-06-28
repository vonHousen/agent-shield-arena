"""Application configuration loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Bifrost LLM gateway configuration.

    Values are loaded from .env file or environment variables.
    """

    bifrost_api_base: str = Field(description="Bifrost gateway base URL")
    bifrost_api_key: str = Field(description="Bifrost API key")
    bifrost_model: str = Field(default="azure/gpt-5.4", description="Model identifier for LiteLLM")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()  # ty: ignore[missing-argument]  # pydantic-settings loads values from env
