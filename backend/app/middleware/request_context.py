"""
Request/correlation ID handling.

Every request gets an ID: the client-supplied X-Request-ID header if
present, otherwise a freshly generated UUID4. The ID is stashed on
flask.g so logging and error handlers can include it, and is always
echoed back as the X-Request-ID response header.
"""
import time
import uuid

from flask import g, request


def register_request_context(app):
    @app.before_request
    def _assign_request_id():
        incoming = request.headers.get("X-Request-ID")
        g.request_id = incoming if incoming else str(uuid.uuid4())
        g.request_start_time = time.monotonic()

    @app.after_request
    def _attach_request_id_header(response):
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response
