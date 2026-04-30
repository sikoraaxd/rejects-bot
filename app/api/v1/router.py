from fastapi import APIRouter

from app.api.v1.routes import cases, chat, health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
