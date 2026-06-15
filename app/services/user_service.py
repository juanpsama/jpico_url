import hashlib
from datetime import datetime, timedelta, timezone
from typing_extensions import Annotated

from fastapi import HTTPException
from fastapi.params import Depends
from sqlmodel import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.core.db import get_db_session
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.token import RefreshTokenCreate, Token
from app.models.user import User, UserCreate, UserPublic, UserUpdate, UserCreateHashPassword

from .base_service import BaseService
from .refresh_token_service import RefreshTokenService, get_refresh_token_service


def user_to_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
    )


class UserService(BaseService[UserPublic, UserCreate, UserUpdate]):

    def __init__(self, db_session: Session, refresh_token_service: RefreshTokenService):
        super().__init__(User, db_session)
        self.refresh_token_service = refresh_token_service

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _generate_token(self, user_id: int) -> Token:
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        hashed = self.hash_refresh_token(refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES,
        )
        self.refresh_token_service.create(
            RefreshTokenCreate(
                user_id=user_id,
                hashed_refresh_token=hashed,
                expires_at=expires_at,
            )
        )
        return Token(access_token=access_token, refresh_token=refresh_token)

    def register(self, user_create_public: UserCreate) -> Token:
        existing_username = self.search_first(User.username == user_create_public.username)
        if existing_username is not None:
            raise HTTPException(status_code=409, detail="Username already taken")
        existing_email = self.search_first(User.email == user_create_public.email)
        if existing_email is not None:
            raise HTTPException(status_code=409, detail="Email already registered")
        user_create = UserCreateHashPassword(
            username=user_create_public.username,
            email=user_create_public.email,
            hashed_password=hash_password(user_create_public.password),
        )
        user = self.create(user_create)
        return self._generate_token(user.id)

    def auth(self, username: str, password: str) -> Token:
        user = self.search_first(User.username == username)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return self._generate_token(user_id=user.id)

    def refresh(self, raw_refresh_token: str) -> Token:
        payload = decode_token(raw_refresh_token)
        if payload is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        if payload.type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user = self.db_session.get(User, int(payload.sub))
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        hashed = self.hash_refresh_token(raw_refresh_token)
        stored = self.refresh_token_service.find_by_hash(hashed)
        if stored is None:
            raise HTTPException(status_code=401, detail="Token not found")
        if stored.is_revoked:
            raise HTTPException(status_code=401, detail="Token has been revoked")
        if stored.expires_at.replace(tzinfo=None) < datetime.now(timezone.utc).replace(tzinfo=None):
            raise HTTPException(status_code=401, detail="Token has expired")

        self.refresh_token_service.revoke(stored.id)
        return self._generate_token(user.id)


def get_user_service(
    db_session: Annotated[Session, Depends(get_db_session)],
    refresh_token_service: Annotated[RefreshTokenService, Depends(get_refresh_token_service)],
) -> UserService:
    return UserService(db_session, refresh_token_service)
