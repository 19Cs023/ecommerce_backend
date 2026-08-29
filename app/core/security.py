"""
Password hashing + JWT issuing/verification.

WHY PASSLIB/BCRYPT:
Never store plaintext passwords, and never write your own hashing.
Bcrypt automatically salts each password and is deliberately slow
(tunable "rounds"), which makes brute-forcing leaked hashes expensive.
This is a solved problem -- use a vetted library, don't reinvent it.

WHY JWT FOR AUTH:
A JSON Web Token is a signed (not encrypted) blob containing claims
(e.g. "user id 42, expires at time X"). The server can verify the
signature without a database lookup, which is why JWT auth scales
well for stateless APIs -- no server-side session store needed.
Trade-off: you can't "revoke" a JWT before it expires without extra
infra (a blocklist), which is why ACCESS_TOKEN_EXPIRE_MINUTES is kept
short and a separate longer-lived refresh token is used to mint new
access tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt is the scheme; passlib handles the salt + hashing rounds for us.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    `subject` is typically the user's id (as a string). We keep the JWT
    payload minimal ("sub" + "exp" + a "type" marker) -- anything else
    you put in here is base64-readable by anyone holding the token, so
    never stuff secrets (passwords, full profiles) into the payload.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Returns the decoded payload, or None if the signature is invalid or
    the token has expired. Callers decide what to do with None (usually
    raise a 401) -- this function stays dumb and side-effect-free so
    it's trivial to unit test.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
