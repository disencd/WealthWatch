"""UI routes — serves Jinja2 HTML templates for the Alpine.js frontend."""

import os

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(include_in_schema=False)

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "templates")
templates = Jinja2Templates(directory=os.path.abspath(_TEMPLATE_DIR))

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


def _ctx(request: Request, **extra):
    return {"request": request, "google_client_id": GOOGLE_CLIENT_ID, **extra}


# ── Auth pages ──
@router.get("/login")
async def login(request: Request):
    return templates.TemplateResponse("login.html", _ctx(request))


@router.get("/register")
async def register(request: Request):
    return templates.TemplateResponse("register.html", _ctx(request))


# ── App pages ──
_PAGES = {
    "/": "dashboard.html",
    "/dashboard": "dashboard.html",
    "/networth": "networth.html",
    "/accounts": "accounts.html",
    "/investments": "investments.html",
    "/transactions": "transactions.html",
    "/budgets": "budgets.html",
    "/recurring": "recurring.html",
    "/rules": "rules.html",
    "/reports": "reports.html",
    "/cashflow": "cashflow.html",
    "/family": "family.html",
}

for _path, _template in _PAGES.items():

    def _make_handler(tmpl: str):
        async def handler(request: Request):
            return templates.TemplateResponse(tmpl, _ctx(request))

        return handler

    router.add_api_route(_path, _make_handler(_template), methods=["GET"])
