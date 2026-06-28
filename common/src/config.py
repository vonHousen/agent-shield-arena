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

    attack_max_messages: int = Field(default=10, description="Attack Agent message budget per conversation")
    runner_max_turns: int = Field(default=12, description="Runner hard ceiling (safety net, > attack budget)")
    runner_turn_delay_seconds: float = Field(default=0.0, description="Pause between turns for demo pacing")

    arena_rounds: int = Field(default=3, description="Number of arena rounds in a multi-round session")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()  # ty: ignore[missing-argument]  # pydantic-settings loads values from env
