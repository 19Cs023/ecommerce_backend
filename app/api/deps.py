"""
Reusable FastAPI dependencies -- mainly the "who is making this
request" chain.

WHY OAuth2PasswordBearer EVEN THOUGH WE DON'T USE OAUTH2 PROPERLY:
It's a FastAPI convenience class that (a) tells the auto-generated
OpenAPI docs to render the "Authorize" button and bearer-token input,
and (b) extracts the `Authorization: Bearer <token>` header for you.
We still issue and verify our own JWTs manually (see core/security.py)
-- this class is just the "extract the header" plumbing, not a full
OAuth2 server implementation.

WHY get_current_user AND get_current_active_user ARE SEPARATE:
Splitting "who is this" from "are they allowed to do things" lets an
endpoint like "resend verification email" depend on just
`get_current_user` (works even for a not-yet-activated account) while
almost everything else depends on `get_current_active_user` (401s
disabled accounts). Layering small dependencies is more flexible than
one monolithic `get_current_user_and_check_everything`.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.crud.user import user as user_crud
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(reusable_oauth2),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        # Explicitly rejecting refresh tokens used as access tokens matters:
        # otherwise a leaked long-lived refresh token could be used
        # directly against every protected endpoint, defeating the whole
        # point of having short-lived access tokens.
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = user_crud.get(db, id=int(user_id))
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    A dependency that itself depends on another dependency -- FastAPI
    resolves the whole chain (token -> user -> active check -> role
    check) automatically. Any admin-only route just declares
    `Depends(get_current_admin_user)` and gets all four checks for free.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user
