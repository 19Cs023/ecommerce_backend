"""
Auth endpoints: register, login, refresh.

WHY LOGIN USES OAuth2PasswordRequestForm (form data) INSTEAD OF JSON:
This isn't our choice of taste -- it's what the OAuth2 "password flow"
spec expects, and FastAPI's auto-generated docs "Authorize" button
specifically POSTs form-encoded `username`/`password` fields. We map
`username` to our `email` field. Every other endpoint in this API
uses JSON bodies; login is the one deliberate exception, for
interactive-docs compatibility.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.crud.user import user as user_crud
from app.db.session import get_db
from app.schemas.user import Token, UserCreate, UserRead

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = user_crud.get_by_email(db, email=user_in.email)
    if existing:
        # 400, not 409: we deliberately don't leak "which exact field
        # conflicted" beyond "email already registered" -- fine here
        # since email uniqueness on signup is not sensitive information,
        # but the general instinct ("what does this error reveal to an
        # attacker probing for valid accounts?") is worth carrying into
        # other apps, e.g. login errors below.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    return user_crud.create(db, obj_in=user_in)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = user_crud.authenticate(db, email=form_data.username, password=form_data.password)
    if user is None:
        # SAME error message whether the email doesn't exist or the
        # password is wrong. A different message for each ("no such
        # user" vs "wrong password") lets an attacker enumerate valid
        # emails by trying logins and watching which error comes back.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    subject = str(user.id)
    return Token(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


@router.post("/refresh", response_model=Token)
def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    """
    Exchanges a valid (non-expired) refresh token for a new access
    token, WITHOUT requiring the user to re-enter their password. This
    is the entire point of having two token types: the short-lived
    access token limits the damage window if it leaks, while the
    refresh token lets the client stay "logged in" for a longer period.
    """
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    user = user_crud.get(db, id=int(user_id)) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    subject = str(user.id)
    return Token(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),  # rotate: issue a fresh refresh token too
    )
