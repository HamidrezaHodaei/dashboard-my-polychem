"""
Application factory for the PolyChem Automation System backend.

create_app() is the single entrypoint used by run.py (local dev),
wsgi.py (future production server), and the pytest fixtures (tests/conftest.py).
No global `app` object exists anywhere in this codebase — everything is
built inside the factory and returned, which is what keeps multiple
configs (dev/testing/production) and test isolation clean.
"""
from flask import Flask

from app.config import get_config
from app.extensions import db, migrate, cors, limiter, jwt
from app.middleware.error_handlers import register_error_handlers
from app.middleware.request_context import register_request_context
from app.middleware.logging_middleware import register_logging
from app.middleware.security_headers import register_security_headers


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)

    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Persian text must round-trip end to end: MySQL connection in utf8mb4 (decided from the
    # URI actually in use, so SQLite test runs are unaffected) and JSON written as real UTF-8
    # characters instead of \\uXXXX escapes.
    if str(app.config.get("SQLALCHEMY_DATABASE_URI", "")).startswith("mysql"):
        options = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})
        options["connect_args"] = {**options.get("connect_args", {}), "charset": "utf8mb4"}
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = options
    app.json.ensure_ascii = False

    _init_extensions(app)
    _register_middleware(app)
    _register_blueprints(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)

    # Import every core/RBAC model exactly once, before any migration,
    # create_all(), or blueprint code runs, so they're registered on
    # db.metadata (required for `flask db migrate` autogenerate and for
    # tests' db.create_all()). See app/core/models_registry.py. Plain
    # import — no app context needed just to define model classes.
    from app.core import models_registry  # noqa: F401

    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )
    limiter.init_app(app)
    jwt.init_app(app)


def _register_middleware(app: Flask) -> None:
    # Order matters: request ID first (other middleware/handlers may want
    # it), then logging, then security headers, then error handlers.
    register_request_context(app)
    register_logging(app)
    register_security_headers(app)
    register_error_handlers(app)


def _register_blueprints(app: Flask) -> None:
    from app.core.health.routes import bp as health_bp
    from app.core.auth.routes import bp as auth_bp
    from app.core.organizations.routes import bp as organizations_bp
    from app.core.departments.routes import bp as departments_bp
    from app.core.teams.routes import bp as teams_bp
    from app.core.users.routes import bp as users_bp
    from app.core.roles.routes import bp as roles_bp
    from app.core.permissions.routes import bp as permissions_bp
    from app.core.authorization.routes import bp as delegations_bp
    from app.modules.tasks.routes import bp as tasks_bp
    from app.modules.suppliers.routes import bp as suppliers_bp
    from app.modules.customers.routes import bp as customers_bp
    from app.modules.crm.routes import bp as crm_bp
    from app.modules.request_samples.routes import bp as request_samples_bp
    from app.modules.logistics.routes import bp as logistics_bp
    from app.modules.notifications.routes import bp as notifications_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)

    # Phase 4 — core CRUD platform blueprints (IMPLEMENTATION_PLAN.md).
    app.register_blueprint(organizations_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(teams_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(roles_bp)
    app.register_blueprint(permissions_bp)
    app.register_blueprint(delegations_bp)

    # Phase 4a — Tasks / Workspace module.
    app.register_blueprint(tasks_bp)

    # Procurement — Suppliers module.
    app.register_blueprint(suppliers_bp)

    # CRM — Customers module.
    app.register_blueprint(customers_bp)

    # CRM — Sales module (sales documents, analytics, product catalogue). Customers come from
    # the customer bank above; nothing here owns a customer table.
    app.register_blueprint(crm_bp)
    # CRM — Request Sample (sample requests: approval, dispatch, follow-ups, customer feedback).
    app.register_blueprint(request_samples_bp)

    # Logistics — transport-company / driver registration module.
    app.register_blueprint(logistics_bp)

    # In-app notifications (header bell) — /api/notifications.
    app.register_blueprint(notifications_bp)

    # Other business module blueprints (CRM, Finance, Warehouse, ...) are
    # added starting later phases — intentionally absent here.