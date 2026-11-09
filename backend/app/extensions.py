"""
Extension instances, created here without binding to an app.

The application factory (app/__init__.py) calls .init_app(app) on each of
these — this is what keeps the app factory pattern clean and avoids any
global app state. Import these instances from here, never re-instantiate
them elsewhere.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)
# Access tokens only -- see app/config.py's Authentication/JWT section
# and app/core/auth/services.py for why refresh tokens are NOT JWTs and
# don't go through this extension.
jwt = JWTManager()


@event.listens_for(Engine, "connect")
def _enforce_sqlite_foreign_keys(dbapi_connection, connection_record):
    """
    SQLite does not enforce FOREIGN KEY constraints unless explicitly told
    to per-connection — unlike MySQL/InnoDB, which enforces them by
    default. Since TestingConfig runs the pytest suite against SQLite
    (README.md §8 / DATABASE.md), FK violations would silently succeed in
    tests without this. This listener only ever fires for SQLite DBAPI
    connections (checked by module name) — it is a no-op for the MySQL
    connections used in dev/production, so it changes no production
    behavior.

    Also sets `defer_foreign_keys=ON`: two Phase 1 tables reference each
    other (departments.manager_user_id -> users.id, use_alter=True;
    users.department_id -> departments.id). On MySQL that's a real
    dialect-supported deferred-ALTER pattern, but the SQLite dialect
    can't emit ALTER TABLE ADD CONSTRAINT, so SQLAlchemy bakes both FKs
    in at CREATE TABLE time regardless of use_alter — the two tables end
    up in a genuine reference cycle on SQLite only. With plain
    `foreign_keys=ON`, `drop_all()` (used by the test fixture teardown)
    fails on whichever of the two tables it drops first, since the other
    still references it. `defer_foreign_keys=ON` postpones the check from
    per-statement to end-of-transaction, so DROP TABLE order within a
    transaction no longer matters — by the time drop_all()'s transaction
    commits, both tables are gone and there's nothing left to violate.
    It does not weaken enforcement of invalid inserts/updates: those are
    still caught, just at commit time instead of immediately — which is
    exactly when the Phase 1 FK-enforcement tests already assert on
    (`db.session.commit()` inside `pytest.raises(IntegrityError)`).
    """
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        # pysqlite (Python's stdlib sqlite3 driver) runs its own implicit
        # transaction management on top of SQLite's: left at its default,
        # it silently opens the real transaction on the first DML/DDL
        # statement rather than on SQLAlchemy's "begin", and treats PRAGMA
        # statements as not starting one at all. That means a PRAGMA
        # issued right after "begin" (see below) can run *before* the
        # real transaction exists, so it has no effect on it — which is
        # exactly what broke `defer_foreign_keys` here. Setting
        # isolation_level=None hands transaction control entirely to
        # SQLAlchemy/us, per SQLAlchemy's documented pysqlite recipe for
        # this exact class of problem.
        dbapi_connection.isolation_level = None


@event.listens_for(Engine, "begin")
def _defer_sqlite_foreign_keys(connection):
    """
    Companion to `_enforce_sqlite_foreign_keys` above.

    Two Phase 1 tables reference each other (departments.manager_user_id
    -> users.id, use_alter=True; users.department_id -> departments.id).
    On MySQL that's a real dialect-supported deferred-ALTER pattern, but
    the SQLite dialect can't emit ALTER TABLE ADD CONSTRAINT, so
    SQLAlchemy bakes both FKs in at CREATE TABLE time regardless of
    use_alter — the two tables end up in a genuine reference cycle on
    SQLite only, and `drop_all()` (used by the test fixture teardown)
    fails on whichever of the two it drops first, since the other still
    references it.

    `PRAGMA defer_foreign_keys=ON` fixes that by postponing the check
    from per-statement to end-of-transaction, so DROP TABLE order no
    longer matters — by the time drop_all()'s transaction commits, both
    tables are gone and there's nothing left to violate. It does not
    weaken enforcement of invalid inserts/updates: those are still
    caught, just at commit time instead of immediately, which is exactly
    when the Phase 1 FK-enforcement tests already assert on
    (`db.session.commit()` inside `pytest.raises(IntegrityError)`).

    It is also transaction-scoped in SQLite — its value automatically
    reverts to OFF at the start of *every* new transaction, unlike
    `PRAGMA foreign_keys` which persists for the life of the connection
    — so it must be re-issued on every "begin", not just once at
    "connect". We drive BEGIN explicitly here (rather than relying on
    pysqlite's own implicit one) precisely so this PRAGMA lands inside
    the transaction it's meant to affect — see the isolation_level note
    above.
    """
    if type(connection.connection.dbapi_connection).__module__.startswith("sqlite3"):
        connection.exec_driver_sql("BEGIN")
        connection.exec_driver_sql("PRAGMA defer_foreign_keys=ON")
