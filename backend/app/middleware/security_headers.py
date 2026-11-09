"""
Baseline security headers. Kept minimal in Phase 0 — a fuller policy
(CSP, HSTS in production, etc.) is refined in the Security phase per
SECURITY.md; this establishes the pattern so it isn't bolted on later.
"""


def register_security_headers(app):
    @app.after_request
    def _set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response
