"""
WSGI entrypoint — reserved for a future production server (e.g. Gunicorn).

NOT used or exercised in Phase 0. No production deployment, process
manager, or reverse proxy configuration exists yet. This file exists only
so the project structure matches ARCHITECTURE.md and future phases don't
need to introduce a new entrypoint file.
"""
import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app(os.environ.get("FLASK_ENV", "production"))
