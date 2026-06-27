"""Project-wide logging configuration.

All application modules should obtain loggers via ``get_logger`` so that
output is routed through the ``arena`` logger hierarchy, leaving third-party
libraries silent unless explicitly configured.
"""

import logging

PROJECT_LOGGER_NAME = "arena"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(*, verbose: bool = False) -> None:
    """Configure the project logger.

    Only the ``arena`` hierarchy is touched — third-party loggers keep
    their default (WARNING) level.

    Args:
        verbose: When True, set the level to DEBUG; otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger(PROJECT_LOGGER_NAME)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the project hierarchy.

    Args:
        name: Typically ``__name__`` of the calling module.
    """
    return logging.getLogger(f"{PROJECT_LOGGER_NAME}.{name}")
