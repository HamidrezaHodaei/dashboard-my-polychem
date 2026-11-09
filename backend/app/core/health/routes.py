"""
GET /api/health

Phase 0's only real endpoint. Reports application status and, where
practical, verifies database connectivity — without leaking any
connection details (no host, user, password, or DSN in the response).
"""
import logging

from flask import Blueprint
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.utils.responses import success_response

logger = logging.getLogger("polychem.health")

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    status = "ok"
    database_status = "unknown"

    try:
        db.session.execute(text("SELECT 1"))
        database_status = "connected"
    except SQLAlchemyError:
        # Never leak the underlying exception (which could include the
        # DSN/credentials) to the client — log it server-side only.
        logger.exception("Health check database connectivity check failed")
        database_status = "unavailable"
        status = "degraded"

    return success_response(
        data={"status": status, "database": database_status}
    )
