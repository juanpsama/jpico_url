from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter(tags=["Web"],redirect_slashes=False)
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def web_home(request: Request):
    return templates.TemplateResponse(
        request=request,name="main.html", context={"title": ""}
    )

@router.get("/login", response_class=HTMLResponse)
async def web_login(request: Request):
    return templates.TemplateResponse(
        request=request,name="login.html", context={"title": " — Login"}
    )

@router.get("/dashboard", response_class=HTMLResponse)
async def web_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,name="dashboard.html", context={"title": " — Dashboard"}
    )
