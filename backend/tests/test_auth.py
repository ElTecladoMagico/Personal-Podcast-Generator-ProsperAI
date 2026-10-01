import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app import auth

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
ISSUER = "https://test.clerk.example"


@pytest.fixture(autouse=True)
def fake_jwks(monkeypatch):
    key = SimpleNamespace(key=PRIVATE_KEY.public_key())
    monkeypatch.setattr(auth._jwks, "get_signing_key_from_jwt", lambda _token: key)


def make_token(**overrides) -> str:
    now = int(time.time())
    claims = {
        "sub": "user_123",
        "iss": ISSUER,
        "iat": now,
        "exp": now + 60,
        "azp": "http://localhost:5173",
    } | overrides
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, PRIVATE_KEY, algorithm="RS256")


def test_valid_token_returns_claims():
    assert auth.verify_token(make_token(email="a@b.c"))["email"] == "a@b.c"


def test_token_without_azp_is_accepted():
    assert auth.verify_token(make_token(azp=None))["sub"] == "user_123"


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": int(time.time()) - 60},  # expired (beyond the 5 s leeway)
        {"azp": "https://evil.example"},  # unknown authorized party
        {"iss": "https://other.clerk.example"},  # other Clerk instance
        {"sub": None},
    ],  # no subject
)
def test_invalid_tokens_are_rejected(overrides):
    with pytest.raises(jwt.PyJWTError):
        auth.verify_token(make_token(**overrides))


def test_token_signed_with_another_key_is_rejected():
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode({"sub": "x", "iss": ISSUER, "iat": 1, "exp": 2**31}, other, "RS256")
    with pytest.raises(jwt.PyJWTError):
        auth.verify_token(token)


def test_require_admin():
    assert auth.require_admin({"metadata": {"role": "admin"}})
    for claims in ({}, {"metadata": {}}, {"metadata": {"role": "user"}}):
        with pytest.raises(HTTPException) as err:
            auth.require_admin(claims)
        assert err.value.status_code == 403
