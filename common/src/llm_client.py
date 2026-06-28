"""Shared LiteLLM client configured for the Bifrost gateway."""

from typing import Any

import litellm

from common.src.config import settings

litellm.suppress_debug_info = True


class LiteLLMClient:
    """LiteLLM adapter configured from application settings."""

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Return a chat completion response from LiteLLM.

        Args:
            messages: OpenAI-compatible chat messages.
            tools: Optional OpenAI-compatible tool schemas.
        """
        api_base = f"{settings.bifrost_api_base}/litellm"

        if tools is None:
            response = await litellm.acompletion(
                model=settings.bifrost_model,
                api_base=api_base,
                api_key=settings.bifrost_api_key,
                messages=messages,
            )
        else:
            response = await litellm.acompletion(
                model=settings.bifrost_model,
                api_base=api_base,
                api_key=settings.bifrost_api_key,
                messages=messages,
                tools=tools,
            )

        return response.model_dump()
