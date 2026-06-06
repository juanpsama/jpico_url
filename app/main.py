from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import TimeoutError

from .api import health
from .api import url_map

# TODO: create database if not exist on startup

app = FastAPI()

@app.exception_handler(TimeoutError)
async def pool_timeout_handler(request: Request, exc: TimeoutError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Service temporarily unavailable, try again later"},
    )

app.include_router(url_map.router)
app.include_router(health.router, prefix="/health")