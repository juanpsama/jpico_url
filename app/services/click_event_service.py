from typing_extensions import Annotated
from fastapi.params import Depends
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.db import get_db_session, get_engine
from app.models.click_event import ClickEvent, ClickEventCreate, ClickEventPagination, ClickEventPublic, UrlStatsPublic

from .base_service import BaseService


class ClickEventService(BaseService[ClickEventPublic, ClickEventCreate, ClickEventCreate]):

    def __init__(self, db_session: Session):
        super().__init__(ClickEvent, db_session)

    def count_by_url(self, url_map_id: int) -> int:
        return self.db_session.exec(
            select(func.count(self.model.id)).where(self.model.url_map_id == url_map_id)
        ).one()

    def list_by_url(self, url_map_id: int, page: int = 0, per_page: int = 10) -> ClickEventPagination:
        offset = page * per_page
        total = self.db_session.exec(
            select(func.count(self.model.id)).where(self.model.url_map_id == url_map_id)
        ).one()
        data = self.db_session.exec(
            select(self.model)
            .where(self.model.url_map_id == url_map_id)
            .order_by(self.model.clicked_at.desc())
            .offset(offset)
            .limit(per_page)
        ).all()
        return ClickEventPagination(page=page, per_page=per_page, total=total, data=data)

    def stats_by_url(self, url_map_id: int) -> UrlStatsPublic:
        total = self.count_by_url(url_map_id)
        last = self.db_session.exec(
            select(self.model)
            .where(self.model.url_map_id == url_map_id)
            .order_by(self.model.clicked_at.desc())
            .limit(1)
        ).first()
        return UrlStatsPublic(
            url_map_id=url_map_id,
            total_clicks=total,
            last_clicked_at=last.clicked_at if last else None,
        )


def record_click(url_map_id: int, ip: str | None, user_agent: str | None, referer: str | None):
    with Session(get_engine()) as session:
        service = ClickEventService(session)
        service.create(
            ClickEventCreate(
                url_map_id=url_map_id,
                ip_address=ip,
                user_agent=user_agent,
                referer=referer,
            )
        )


def get_click_event_service(db_session: Annotated[Session, Depends(get_db_session)]) -> ClickEventService:
    return ClickEventService(db_session)
