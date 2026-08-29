"""
User-related Pydantic schemas.

WHY SEPARATE SCHEMAS FOR SEPARATE PURPOSES (instead of one User schema
reused everywhere):
- `UserCreate` accepts a plaintext `password` field (needed on signup).
- `UserRead` (the API response) must NEVER include the password hash
  -- if it did, every "get user" response would leak a crackable hash
  to the client. Because `UserRead` simply doesn't declare that field,
  it's structurally impossible to leak it, regardless of what the ORM
  object contains.
- `UserUpdate` makes every field Optional, because PATCH-style updates
  should let the client send only the fields they're changing.

This "different schema per operation" pattern is the single most
important habit to take away from this codebase for any other API you
build: never let one model class also serve as your wire format.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class UserRead(UserBase):
    # `from_attributes=True` lets Pydantic build this schema directly
    # from a SQLAlchemy ORM object (`UserRead.model_validate(user_obj)`)
    # instead of requiring a dict -- it reads attributes off the object.
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: UserRole
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None
