"""
Local development entrypoint.

Usage:
    python run.py

Serves the app on http://localhost:5000. Reads FLASK_ENV from the
environment (via .env, loaded below) to pick the config class —
defaults to 'development' if unset.
"""
import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402  (must load .env before importing app.config)

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=app.config.get("DEBUG", False))
