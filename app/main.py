from fastapi import FastAPI

from .api import health
from .api import url_map

# TODO: create database if not exist on startup

app = FastAPI()

app.include_router(url_map.router)
app.include_router(health.router, prefix="/health")