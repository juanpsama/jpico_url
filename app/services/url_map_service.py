from datetime import datetime, timezone
from typing import Optional
from typing_extensions import Annotated
from sqlalchemy import func

from fastapi.params import Depends
from sqlmodel import Session, select

from app.core.cache import get_redis_cache
from app.core.db import engine, get_db_session
from app.core.cache import RedisCache
from app.models.url_map import UrlMap, UrlMapCreate, UrlMapPublic

from .base_service import BaseService
from .pg_error_handler import pg_error_handler

BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
MAX_VAL = 62 ** 4  # 14776336
PRIME = 748361

class UrlMapService(BaseService[UrlMapPublic, UrlMapCreate, UrlMapCreate]):

    """
    Service class for managing URL mappings. Inherits from BaseService to provide
    CRUD operations for the UrlMap model.
    """

    def __init__(self, db_session: Session, cache: Optional[RedisCache] = None):
        super().__init__(UrlMap, db_session)
        self.cache = cache

    def _encode_base62(self, num: int) -> str:
        """Encodes an integer into a 4-character Base62 string."""
        if num == 0:
            return BASE62_ALPHABET[0] * 4
        
        chars = []
        while num > 0:
            remainder = num % 62
            chars.append(BASE62_ALPHABET[remainder])
            num //= 62
            
        # Pad to exactly 4 characters
        while len(chars) < 4:
            chars.append(BASE62_ALPHABET[0])
            
        return "".join(reversed(chars))

    def _generate_short_code(self, base_id: int) -> str:
        """Generates a non-obvious short code using LCG."""
        obfuscated_id = (base_id * PRIME) % MAX_VAL
        return self._encode_base62(obfuscated_id)

    def list_by_owner(self, owner_id: int, page: int = 0, per_page: int = 10, order_by: str | None = None):
        offset = page * per_page
        total_count = self.db_session.exec(
            select(func.count(self.model.id)).where(self.model.owner_id == owner_id)
        ).one()
        query = select(self.model).where(self.model.owner_id == owner_id)
        if order_by:
            order_parts = order_by.split(":")
            column_name = order_parts[0]
            direction = order_parts[1].lower() if len(order_parts) > 1 else "asc"
            if hasattr(self.model, column_name):
                column = getattr(self.model, column_name)
                query = query.order_by(column.asc() if direction == "asc" else column.desc())
        data = self.db_session.exec(query.offset(offset).limit(per_page)).all()
        return {"page": page, "per_page": per_page, "total": total_count, "data": data}

    @pg_error_handler
    def create(self, obj: UrlMapCreate, owner_id: int | None = None) -> UrlMap:
        db_obj = self.model(**obj.model_dump())
        db_obj.create_date = datetime.now(timezone.utc)
        db_obj.owner_id = owner_id

        self.db_session.add(db_obj)
        self.db_session.flush()

        db_obj.short_url_code = self._generate_short_code(db_obj.id)

        self.db_session.commit()
        self.db_session.refresh(db_obj)
        return db_obj

    async def get_by_short_code(self, short_code: str) -> dict[str, str] | None:
        if self.cache is None:
            record = self.search_first(UrlMap.short_url_code == short_code)
            if record is None:
                return None
            return {"id": str(record.id), "original_url": record.original_url, "short_url_code": record.short_url_code}

        def loader(_key: str) -> Optional[dict[str, str]]:
            with Session(engine) as session:
                record = session.exec(
                    select(UrlMap).where(UrlMap.short_url_code == short_code)
                ).first()
                if record is None:
                    return None
                return {"id": str(record.id), "original_url": record.original_url, "short_url_code": record.short_url_code}

        cached, _hit, _latency = await self.cache.get(short_code, loader)
        return cached

def get_url_map_service(db_session: Annotated[Session, Depends(get_db_session)], cache: Annotated[RedisCache, Depends(get_redis_cache)]) -> UrlMapService:
    """
    Dependency function to provide an instance of UrlMapService with a database session.
    """
    return UrlMapService(db_session, cache)


def get_redirect_service(cache: Annotated[RedisCache, Depends(get_redis_cache)]) -> UrlMapService:
    """
    Dependency function for the redirect route.
    Inject only the cache so cache hits never consume a DB connection.
    The loader inside get_by_short_code opens a short-lived session only on cache miss.
    """
    return UrlMapService(None, cache)
