from __future__ import annotations

import logging
import re

_SECRET_QUERY_PATTERN = re.compile(r"((?:token|access_token)=)[^&\s\"']+", re.IGNORECASE)


class RedactSecretsFilter(logging.Filter):
    """Masque les jetons passés en query string (ex. `/ws/game-config?token=...` journalisé par uvicorn)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and record.args:
            record.args = tuple(_redact(arg) if isinstance(arg, str) else arg for arg in record.args)
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        return True


def _redact(value: str) -> str:
    return _SECRET_QUERY_PATTERN.sub(r"\1***", value)


def install_secret_redaction(*logger_names: str) -> None:
    redactor = RedactSecretsFilter()
    for name in logger_names:
        logger = logging.getLogger(name)
        if not any(isinstance(existing, RedactSecretsFilter) for existing in logger.filters):
            logger.addFilter(redactor)
