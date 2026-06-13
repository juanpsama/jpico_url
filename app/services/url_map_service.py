from datetime import datetime, timezone
from typing import Optional
from typing_extensions import Annotated

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

    @pg_error_handler
    def create(self, obj: UrlMapCreate) -> UrlMap:
        db_obj = self.model(**obj.model_dump())
        # Populate defaults required before flushing
        db_obj.create_date = datetime.now(timezone.utc)
        
        self.db_session.add(db_obj)
        self.db_session.flush() 
        
        # Now generate the actual short code and update
        db_obj.short_url_code = self._generate_short_code(db_obj.id)
        
        self.db_session.commit()
        self.db_session.refresh(db_obj)
        return db_obj

    async def get_by_short_code(self, short_code: str) -> str | None:
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
