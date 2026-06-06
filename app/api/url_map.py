from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.models.url_map import UrlMap, UrlMapCreate, UrlMapPagination, UrlMapPublic
from app.services.url_map_service import UrlMapService, get_url_map_service


router = APIRouter(tags=["Url Mapping"])

@router.get("/urls", response_model=UrlMapPagination)
async def list_url_maps(
    url_map_service: Annotated[UrlMapService, Depends(get_url_map_service)],
    page: int = 0,
    per_page: int = 10,
    order_by: str | None = None,
):
    return url_map_service.list(
        page=page, per_page=per_page, order_by=order_by,
    )

@router.post("/shorten", response_model=UrlMapPublic)  # TODO: define response model
async def create_url_map(
        url_map_data: UrlMapCreate,
        url_map_service: Annotated[UrlMapService, Depends(get_url_map_service)]):
    
    return url_map_service.create(url_map_data)

@router.get("/{short_code}", response_class=RedirectResponse)
async def get_url_map(
        short_code: str,
        url_map_service: Annotated[UrlMapService, Depends(get_url_map_service)]):

    cached = await url_map_service.get_by_short_code(short_code)
    if cached is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    return RedirectResponse(url=cached["original_url"], status_code=status.HTTP_302_FOUND)

# This endpoint is intended for benchmarking purposes, it bypasses the cache layer to directly test the database retrieval performance.
@router.get("/no-cache/{short_code}", response_class=RedirectResponse)
async def get_url_map_no_cache(
        short_code: str,
        url_map_service: Annotated[UrlMapService, Depends(get_url_map_service)]):

    url_map = url_map_service.search_first(UrlMap.short_url_code == short_code)

    if url_map is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    return RedirectResponse(url=url_map.original_url, status_code=status.HTTP_302_FOUND)