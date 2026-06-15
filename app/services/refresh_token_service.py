from datetime import datetime, timezone
from typing_extensions import Annotated

from fastapi.params import Depends
from sqlmodel import Session

from app.core.db import get_db_session
from app.models.token import (
    RefreshToken,
    RefreshTokenCreate,
    RefreshTokenPublic,
)

from .base_service import BaseService


class RefreshTokenService(BaseService[RefreshTokenPublic, RefreshTokenCreate, RefreshTokenCreate]):

    def __init__(self, db_session: Session):
        super().__init__(RefreshToken, db_session)

    def find_by_hash(self, hashed_token: str) -> RefreshToken | None:
        return self.search_first(RefreshToken.hashed_refresh_token == hashed_token)

    def revoke(self, token_id: int) -> None:
        token = self.get(token_id)
        token.is_revoked = True
        self.db_session.commit()

    def revoke_by_hash(self, hashed_token: str) -> None:
        token = self.find_by_hash(hashed_token)
        if token is not None:
            token.is_revoked = True
            self.db_session.commit()

    def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        expired = self.search(RefreshToken.expires_at < now)
        count = len(expired)
        for token in expired:
            self.db_session.delete(token)
        self.db_session.commit()
        return count


def get_refresh_token_service(
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RefreshTokenService:
    return RefreshTokenService(db_session)
