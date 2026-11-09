"""Password hashing tests -- app/core/auth/services.py."""
from app.core.auth import services


def test_hash_password_produces_argon2_hash(app):
    hashed = services.hash_password("Correct-Horse-1")
    assert hashed != "Correct-Horse-1"
    assert hashed.startswith("$argon2")


def test_correct_password_verifies(app):
    hashed = services.hash_password("Correct-Horse-1")
    assert services.verify_password("Correct-Horse-1", hashed) is True


def test_incorrect_password_fails(app):
    hashed = services.hash_password("Correct-Horse-1")
    assert services.verify_password("Wrong-Password-2", hashed) is False


def test_plaintext_password_is_never_the_stored_value(app):
    from .factories import make_user

    user = make_user(password="Another-Secret-3")
    assert user.password_hash != "Another-Secret-3"
    assert "Another-Secret-3" not in user.password_hash
