from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import models
from ..dependencies import get_optional_user

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="templates")


def _page(request: Request, template: str, **ctx):
    return templates.TemplateResponse(template, {"request": request, **ctx})


@router.get("/")
def landing(request: Request):
    return _page(request, "public/home.html")


@router.get("/about")
def about(request: Request):
    return _page(request, "public/about.html")


@router.get("/solar")
def solar(request: Request):
    return _page(request, "public/solar.html")


@router.get("/how-it-works")
def how_it_works(request: Request):
    return _page(request, "public/how_it_works.html")


@router.get("/services")
def services_page(request: Request):
    return _page(request, "public/services.html")


@router.get("/projects")
def projects_page(request: Request):
    return _page(request, "public/projects.html")


@router.get("/faq")
def faq_page(request: Request):
    return _page(request, "public/faq.html")


@router.get("/contact")
def contact_page(request: Request):
    return _page(request, "public/contact.html")


@router.get("/login")
def client_login_page(request: Request, user: models.User = Depends(get_optional_user)):
    if user and user.role == models.RoleName.CLIENT:
        return RedirectResponse("/client/dashboard")
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/staff-login")
def staff_login_page(request: Request):
    return templates.TemplateResponse("auth/staff_login.html", {"request": request})


@router.get("/client/dashboard")
def client_dashboard_page(request: Request):
    return templates.TemplateResponse("client/dashboard.html", {"request": request})


@router.get("/admin/dashboard")
def admin_dashboard_page(request: Request):
    return templates.TemplateResponse("admin/console.html", {"request": request, "role": "ADMIN", "role_label": "Admin"})


@router.get("/super-admin/dashboard")
def super_admin_dashboard_page(request: Request):
    return templates.TemplateResponse("admin/console.html", {"request": request, "role": "SUPER_ADMIN", "role_label": "Super Admin"})


@router.get("/primary-admin/dashboard")
def primary_admin_dashboard_page(request: Request):
    return templates.TemplateResponse("admin/console.html", {"request": request, "role": "PRIMARY_ADMIN", "role_label": "Primary Admin"})
