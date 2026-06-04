from datetime import datetime

from sqlmodel import SQLModel, Field

from app.models.pagination import PaginationBase

class UrlMapBase(SQLModel):
    original_url: str
    create_date: datetime   
    # create_user_id: int

class UrlMapCreate(SQLModel):
    original_url: str    

class UrlMapPublic(UrlMapBase):
    # id: int
    short_url_code: str
    # consider adding this field on the database or generating on the get method
    # what is more efficient ?
    # shorten_url : str complete url with domain, 

class UrlMap(UrlMapBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    short_url_code: str | None = Field(index=True, unique=True, nullable=True)

class UrlMapPagination(PaginationBase):
    data: list[UrlMapPublic]