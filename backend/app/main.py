import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.services import pipeline, run_store

FRONTEND_DIR = Path(__file__).parent / "frontend"
ORIGINS = {
    settings.FRONTEND_HOST,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8100",
    "http://127.0.0.1:8100",
}


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{(route.tags or ['app'])[0]}-{route.name}"


@asynccontextmanager
async def lifespan(_app):
    if os.environ.get("SQL_LAB_IMPORT_LEGACY") != "0":
        await asyncio.to_thread(run_store.reconcile_legacy)
    pipeline.ON_UPDATE = run_store.save_meta
    try:
        yield
    finally:
        await asyncio.to_thread(pipeline.shutdown)
        pipeline.ON_UPDATE = None


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ORIGINS),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"]
)


@app.middleware("http")
async def local_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin and origin not in ORIGINS:
        return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
    return await call_next(request)


app.include_router(api_router, prefix=settings.API_V1_STR)


# Unknown API paths must not fall through to the SPA's index.html.
@app.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
def unknown_api():
    return JSONResponse({"detail": "Not found"}, status_code=404)


if FRONTEND_DIR.exists():
    app.frontend("/", directory=FRONTEND_DIR)
