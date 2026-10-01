"""Clerk session tokens: verify the JWT locally with Clerk's public keys (JWKS), no API calls.

The custom session claims (`metadata`, `email`, `name`) are configured in the Clerk instance;
see docs/plans/README.md.
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.config import settings
from app.db import DbSession
from app.models import Event, User

_jwks = jwt.PyJWKClient(
    f"{settings.clerk_issuer}/.well-known/jwks.json", cache_keys=True, lifespan=3600
)
_bearer = HTTPBearer(auto_error=False)


def verify_token(token: str) -> dict:
    key = _jwks.get_signing_key_from_jwt(token).key
    claims = jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        issuer=settings.clerk_issuer,
        leeway=5,
        options={"require": ["exp", "iat", "sub"]},
    )
    # `azp` = origin that requested the token; stops tokens minted for other sites.
    azp = claims.get("azp")
    if azp and azp not in settings.clerk_authorized_parties:
        raise jwt.InvalidTokenError(f"unauthorized party: {azp}")
    return claims


def get_claims(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    if creds is None:
        raise HTTPException(401, "Missing bearer token")
    try:
        return verify_token(creds.credentials)
    except jwt.PyJWTError as err:
        raise HTTPException(401, "Invalid or expired session token") from err


Claims = Annotated[dict, Depends(get_claims)]


def current_user(claims: Claims, session: DbSession) -> User:
    """Upsert the user by Clerk id; refresh email/name from the token on every call."""
    email, name = claims.get("email") or None, claims.get("name") or None
    user = session.exec(select(User).where(User.clerk_id == claims["sub"])).first()
    if user is None:
        user = User(clerk_id=claims["sub"], email=email, display_name=name)
        session.add(user)
        session.add(Event(user_id=user.id, type="user_signed_up"))
        try:
            session.commit()
        except IntegrityError:  # two first requests raced; the other one created the user
            session.rollback()
            user = session.exec(select(User).where(User.clerk_id == claims["sub"])).one()
    elif (user.email, user.display_name) != (email, name):
        user.email, user.display_name = email, name
        session.commit()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_admin(claims: Claims) -> dict:
    if (claims.get("metadata") or {}).get("role") != "admin":
        raise HTTPException(403, "Admins only")
    return claims
