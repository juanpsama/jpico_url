from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship

from .user import User


class Token(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(SQLModel):
    refresh_token: str


class RefreshTokenCreate(SQLModel):
    user_id: int
    hashed_refresh_token: str
    expires_at: datetime


class RefreshTokenPublic(SQLModel):
    id: int
    user_id: int | None
    is_revoked: bool
    created_at: datetime
    expires_at: datetime


class RefreshToken(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id")
    hashed_refresh_token: str = Field(index=True)
    is_revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime

    user: User = Relationship(back_populates="tokens")