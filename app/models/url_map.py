from datetime import datetime

from sqlmodel import SQLModel, Field

from app.models.pagination import PaginationBase

class UrlMapBase(SQLModel):
    original_url: str
    create_date: datetime

class UrlMapCreate(SQLModel):
    original_url: str

class UrlMapPublic(UrlMapBase):
    short_url_code: str
    owner_id: int | None = None

class UrlMap(UrlMapBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    short_url_code: str | None = Field(index=True, unique=True, nullable=True)
    owner_id: int | None = Field(default=None, foreign_key="user.id", nullable=True)

class UrlMapPagination(PaginationBase):
    data: list[UrlMapPublic]