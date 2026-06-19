from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class ClickEvent(SQLModel, table=True):
    __tablename__ = "clickevent"

    id: int | None = Field(default=None, primary_key=True)
    url_map_id: int = Field(foreign_key="urlmap.id", index=True)
    clicked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: str | None = None
    user_agent: str | None = None
    referer: str | None = None
    country: str | None = None


class ClickEventCreate(SQLModel):
    url_map_id: int
    ip_address: str | None = None
    user_agent: str | None = None
    referer: str | None = None


class ClickEventPublic(SQLModel):
    id: int
    url_map_id: int
    clicked_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    referer: str | None = None
    country: str | None = None


class ClickEventPagination(SQLModel):
    page: int
    per_page: int
    total: int
    data: list[ClickEventPublic] = []


class UrlStatsPublic(SQLModel):
    url_map_id: int
    total_clicks: int
    last_clicked_at: datetime | None = None
