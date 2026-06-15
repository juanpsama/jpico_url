from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth_deps import get_current_user
from app.models.token import Token, TokenRefresh
from app.models.user import User, UserCreate, UserPublic
from app.services.user_service import UserService, get_user_service, user_to_public

router = APIRouter(tags=["Auth"], prefix="/auth")


@router.post("/register", response_model=Token)
async def register(
    user_create: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    return user_service.register(user_create)


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[UserService, Depends(get_user_service)],
):
    return service.auth(form_data.username, form_data.password)


@router.post("/refresh", response_model=Token)
async def refresh(
    body: TokenRefresh,
    service: Annotated[UserService, Depends(get_user_service)],
):
    return service.refresh(body.refresh_token)


@router.get("/me", response_model=UserPublic)
async def me(user: Annotated[User, Depends(get_current_user)]):
    return user_to_public(user)

