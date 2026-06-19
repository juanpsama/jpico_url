from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import TimeoutError

from .api import auth
from .api import health
from .api import url_map
from .api import web
from .core.config import settings
from .core.db import engine 
from .services.click_event_batcher import ClickEventBatcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    batcher = ClickEventBatcher(
        engine=engine,
        flush_interval=settings.FLUSH_INTERVAL_SECONDS,
        batch_size=settings.BATCH_SIZE,
        max_queue_size=settings.MAX_QUEUE_SIZE,
    )
    await batcher.start()
    app.state.click_batcher = batcher
    yield
    await batcher.stop()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(TimeoutError)
async def pool_timeout_handler(request: Request, exc: TimeoutError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Service temporarily unavailable, try again later"},
    )


app.include_router(auth.router)
app.include_router(url_map.router)
app.include_router(health.router, prefix="/health")
app.include_router(web.router, prefix="/web")