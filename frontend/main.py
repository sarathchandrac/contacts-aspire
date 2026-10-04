import asyncio
import os

import httpx
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Contacts Frontend")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Injected by Aspire via .WithReference(api) (service discovery)
API_URL = (
    os.environ.get("services__api__http__0")
    or os.environ.get("services__api__https__0")
    or os.environ.get("API_URL", "http://localhost:8000")
)


async def fetch(client: httpx.AsyncClient, path: str):
    try:
        resp = await client.get(f"{API_URL}{path}")
        resp.raise_for_status()
        return resp.json(), None
    except httpx.HTTPError as exc:
        return None, f"{path}: {exc}"


@app.get("/")
async def index(request: Request):
    async with httpx.AsyncClient(timeout=10) as client:
        (contacts, e1), (users, e2), (analytics, e3) = await asyncio.gather(
            fetch(client, "/contacts"), fetch(client, "/users"), fetch(client, "/analytics")
        )
    errors = [e for e in (e1, e2, e3) if e]
    return templates.TemplateResponse(
        request,
        "index.html",
        {"contacts": contacts or [], "users": users or [], "analytics": analytics, "errors": errors},
    )
