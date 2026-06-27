"""Project-wide logging configuration.

All application modules should obtain loggers via ``get_logger`` so that
output is routed through the ``arena`` logger hierarchy, leaving third-party
libraries silent unless explicitly configured.
"""

import logging
from pathlib import Path

PROJECT_LOGGER_NAME = "arena"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_LOG_FILE = Path("data/logs/arena.log")


def setup_logging(*, verbose: bool = False, log_file: Path = DEFAULT_LOG_FILE) -> None:
    """Configure the project logger with console and file output.

    Only the ``arena`` hierarchy is touched — third-party loggers keep
    their default (WARNING) level.

    Args:
        verbose: When True, set the level to DEBUG; otherwise INFO.
        log_file: Path to the log file. Parent directories are created automatically.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger(PROJECT_LOGGER_NAME)
    logger.setLevel(level)

    if not logger.handlers:
        formatter = logging.Formatter(LOG_FORMAT)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the project hierarchy.

    Args:
        name: Typically ``__name__`` of the calling module.
    """
    return logging.getLogger(f"{PROJECT_LOGGER_NAME}.{name}")
