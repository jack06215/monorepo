"""Logging utilities."""

import logging


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a configured logger without duplicating handlers.

    This function is safe to call multiple times and is suitable for
    libraries, CLIs, tests, and long-running processes.

    Args:
        name: Logger name (usually __name__).
        level: Logging level.

    Returns:
        A configured logger.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.setLevel(level)
        logger.addHandler(handler)

    # Prevent double logging via root logger
    logger.propagate = False

    return logger
