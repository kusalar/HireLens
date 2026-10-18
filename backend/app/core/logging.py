import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class StructuredJSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects for production ingestion
    (Datadog, AWS CloudWatch, ElasticSearch, Grafana Loki).
    Excludes sensitive fields like passwords, tokens, API keys, and card credentials.
    """

    SENSITIVE_KEYS = {
        "password",
        "hashed_password",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "secret_key",
        "api_key",
        "authorization",
        "card_number",
        "cvv",
        "razorpay_key_secret",
        "stripe_secret_key",
    }

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func_name": record.funcName,
            "line_no": record.lineno,
        }

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Sanitize any extra attributes
        for key, val in record.__dict__.items():
            if key not in log_obj and not key.startswith("_"):
                lower_key = key.lower()
                if any(sensitive in lower_key for sensitive in self.SENSITIVE_KEYS):
                    log_obj[key] = "[REDACTED]"
                else:
                    try:
                        # Ensure serializable
                        json.dumps(val)
                        log_obj[key] = val
                    except Exception:
                        log_obj[key] = str(val)

        return json.dumps(log_obj)


def setup_logging(level: str = "INFO", structured: bool = False):
    """
    Configure application-wide logging.
    If structured is True, uses StructuredJSONFormatter.
    """
    handler = logging.StreamHandler(sys.stdout)
    if structured:
        handler.setFormatter(StructuredJSONFormatter())
    else:
        fmt = "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
        handler.setFormatter(logging.Formatter(fmt))

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Avoid duplicate handlers
    root_logger.handlers = [handler]
