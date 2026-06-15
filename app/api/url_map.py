from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.core.auth_deps import get_current_user, get_optional_user
from app.models.url_map import UrlMap, UrlMapCreate, UrlMapPagination, UrlMapPublic
from app.models.user import User
from app.services.url_map_service import UrlMapService, get_redirect_service, get_url_map_service


router = APIRouter(tags=["Url Mapping"])

@router.get("/urls", response_model=UrlMapPagination, dependencies=[Depends(get_current_user)])
async def list_url_maps(
    url_map_service: Annotated[UrlMapService, Depends(get_url_map_service)],
    page: int = 0,
    per_page: int = 10,
    order_by: str | None = None,
):
    return url_map_service.list(
        page=page, per_page=per_page, order_by=order_by,
    )

@router.post("/shorten", response_model=UrlMapPublic)
async def create_url_map(
    url_map_data: UrlMapCreate,
    url_map_service: Annotated[UrlMapService, Depends(get_url_map_service)],
    current_user: Annotated[User | None, Depends(get_optional_user)] = None,
):
    return url_map_service.create(url_map_data, owner_id=current_user.id if current_user else None)

@router.get("/my-urls", response_model=UrlMapPagination)
async def list_my_urls(
    url_map_service: Annotated[UrlMapService, Depends(get_url_map_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = 0,
    per_page: int = 10,
    order_by: str | None = None,
):
    return url_map_service.list_by_owner(
        owner_id=current_user.id, page=page, per_page=per_page, order_by=order_by,
    )

@router.get("/{short_code}", response_class=RedirectResponse)
async def get_url_map(
    short_code: str,
    url_map_service: Annotated[UrlMapService, Depends(get_redirect_service)],
):
    cached = await url_map_service.get_by_short_code(short_code)
    if cached is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    return RedirectResponse(url=cached["original_url"], status_code=status.HTTP_302_FOUND)

@router.get("/no-cache/{short_code}", response_class=RedirectResponse)
async def get_url_map_no_cache(
    short_code: str,
    url_map_service: Annotated[UrlMapService, Depends(get_url_map_service)],
):
    url_map = url_map_service.search_first(UrlMap.short_url_code == short_code)

    if url_map is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    return RedirectResponse(url=url_map.original_url, status_code=status.HTTP_302_FOUND)