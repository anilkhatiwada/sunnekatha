"""Structured logging helpers with no external runtime dependency."""

import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Render one JSON object per line for container log collectors."""

    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
