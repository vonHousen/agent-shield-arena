"""Shared LiteLLM client configured for the Bifrost gateway."""

from typing import Any

import litellm
from pydantic import BaseModel

from common.src.config import settings
from common.src.exceptions import ContentFilterError

litellm.suppress_debug_info = True

CONTENT_FILTER_SIGNALS = (
    "content_filter",
    "cyber_policy",
    "content was flagged",
    "ResponsibleAIPolicyViolation",
)


def raise_on_content_filter(error: litellm.BadRequestError) -> None:
    """Re-raise as ContentFilterError if the error is a content-policy rejection.

    Args:
        error: The original BadRequestError from litellm/provider.

    Raises:
        ContentFilterError: When the error message matches known content-filter signals.
    """
    error_str = str(error).lower()
    for signal in CONTENT_FILTER_SIGNALS:
        if signal.lower() in error_str:
            raise ContentFilterError(str(error), original_error=error) from error


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

        Raises:
            ContentFilterError: When the provider rejects the request due to content policy.
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

        try:
            response = await litellm.acompletion(**kwargs)
        except litellm.BadRequestError as e:
            raise_on_content_filter(e)
            raise

        return response.model_dump()
