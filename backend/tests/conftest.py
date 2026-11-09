import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    application = create_app("testing")

    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    # use_cookies=False: several auth tests (tests/auth/test_refresh.py)
    # deliberately re-present an OLD refresh_token cookie via an explicit
    # `Cookie` header (see with_refresh_cookie() in tests/auth/factories.py)
    # to exercise reuse/rotation detection. Werkzeug's test client has its
    # own persistent cookie jar that auto-attaches the LATEST Set-Cookie
    # value from prior responses on this client; when both an explicit
    # Cookie header and the jar are present, the jar's value wins and the
    # "old" token you thought you sent is silently replaced by the current
    # one -- making reuse impossible to test and every refresh call look
    # like a fresh, valid one. Disabling the jar here makes the client
    # send exactly the cookies each test passes, nothing more.
    return app.test_client(use_cookies=False)
