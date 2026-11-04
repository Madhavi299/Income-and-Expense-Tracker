from jose import jwt

from backend.app.core.config import ALGORITHM, SECRET_KEY
from backend.app.security import create_access_token, hash_password, verify_password


def test_password_hash_is_salted_and_verifiable():
    first_hash = hash_password("correct horse battery staple")
    second_hash = hash_password("correct horse battery staple")

    assert first_hash != second_hash
    assert verify_password("correct horse battery staple", first_hash)
    assert not verify_password("wrong password", first_hash)


def test_password_verification_rejects_malformed_hashes():
    assert not verify_password("password", "not-a-valid-hash")
    assert not verify_password("password", "invalid$hex-digest")


def test_access_token_contains_user_id_and_expiry():
    token = create_access_token(42)
    claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert claims["sub"] == "42"
    assert claims["exp"] > 0
