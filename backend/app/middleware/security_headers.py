"""
Baseline security headers. Kept minimal in Phase 0 — a fuller policy
(CSP, HSTS in production, etc.) is refined in the Security phase per
SECURITY.md; this establishes the pattern so it isn't bolted on later.
"""


from flask import request


def register_security_headers(app):
    @app.after_request
    def _set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # Private API data must never be stored by a browser/PWA cache or an intermediary. Only JSON answers
        # to /api/* are touched, and only when the route did not choose its own policy (the task-attachment
        # route sets "private, no-cache"); file downloads are left exactly as they were.
        if request.path.startswith("/api/") and response.mimetype == "application/json":
            response.headers.setdefault("Cache-Control", "no-store")
        return response
