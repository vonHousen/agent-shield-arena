"""Shared LiteLLM client configured for the Bifrost gateway."""

from typing import Any

import litellm
from pydantic import BaseModel

from common.src.config import settings

litellm.suppress_debug_info = True


class LiteLLMClient:
    """LiteLLM adapter configured from application settings."""

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: type[BaseModel] | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a chat completion response from LiteLLM.

        Args:
            messages: OpenAI-compatible chat messages.
            tools: Optional OpenAI-compatible tool schemas.
            response_format: Pydantic model class or dict for structured output.
        """
        api_base = f"{settings.bifrost_api_base}/litellm"

        kwargs: dict[str, Any] = {
            "model": settings.bifrost_model,
            "api_base": api_base,
            "api_key": settings.bifrost_api_key,
            "messages": messages,
        }
        if tools is not None:
            kwargs["tools"] = tools
        if response_format is not None:
            kwargs["response_format"] = response_format

        response = await litellm.acompletion(**kwargs)
        return response.model_dump()
