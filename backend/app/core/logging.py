"""
Structured logging configuration.

v0.1 establishes the logging *shape* the whole application will use later:
structured, JSON-capable, request-scoped-friendly fields (request_id,
user_id, etc. will be added by middleware in v0.2+). Nothing sensitive
(passwords, tokens, document content) is ever logged — see the
architecture doc for the full safe-logging policy.
"""

import logging
import sys

from pythonjsonlogger import jsonlogger

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())

    # Avoid duplicate handlers on reload (uvicorn --reload re-imports).
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    formatter: logging.Formatter
    if settings.log_json:
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Quiet noisy third-party loggers at INFO; leave WARNING+ intact.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
