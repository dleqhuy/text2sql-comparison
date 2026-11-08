from fastapi import APIRouter

from app.api.routes import live, utils

api_router = APIRouter()
api_router.include_router(live.router)
api_router.include_router(utils.router)
