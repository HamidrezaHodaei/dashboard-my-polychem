"""
Basic structured request logging.

Logs, per request: HTTP method, path, status code, request ID, duration.

NEVER logged, here or anywhere else in the app: passwords, JWTs, refresh
tokens, database credentials, API keys, or any other secret. This module
only ever touches request metadata (method/path/status/timing), never the
request body or headers that could carry credentials.
"""
import logging
import time

from flask import g, request

logger = logging.getLogger("polychem.request")


def register_logging(app):
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    @app.after_request
    def _log_request(response):
        start = getattr(g, "request_start_time", None)
        duration_ms = round((time.monotonic() - start) * 1000, 2) if start else None
        request_id = getattr(g, "request_id", "-")

        logger.info(
            "method=%s path=%s status=%s request_id=%s duration_ms=%s",
            request.method,
            request.path,
            response.status_code,
            request_id,
            duration_ms,
        )
        return response
