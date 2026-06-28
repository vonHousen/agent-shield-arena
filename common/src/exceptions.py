"""Shared exceptions for the arena."""


class ContentFilterError(Exception):
    """Raised when the LLM provider rejects a request due to content policy.

    Args:
        message: Human-readable description of the rejection.
        original_error: The underlying provider exception, if available.
    """

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message)
        self.original_error = original_error
