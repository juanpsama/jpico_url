from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship



class UserBase(SQLModel):
    username: str = Field(min_length=3, max_length=64)
    email: str = Field(max_length=254)

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

class UserCreateHashPassword(UserBase):
    hashed_password : str

class UserUpdate(UserBase):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    email: str | None = Field(default=None, max_length=254)
    password: str | None = Field(default=None, min_length=8, max_length=128)

class UserPublic(UserBase):
    id: int
    is_active: bool
    created_at: datetime

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=64)
    email: str = Field(index=True, unique=True, max_length=254)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    token_version: int = Field(default=0)

    tokens: list["RefreshToken"] = Relationship(back_populates="user") # noqa: F821
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(default=None)


