from sqlmodel import SQLModel

class PaginationBase(SQLModel):
    page : int
    per_page : int
    total : int
    data: list | None = None