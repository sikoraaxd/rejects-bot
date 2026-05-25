from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import API_V1_PREFIX, API_VERSION, PROJECT_NAME


def create_app() -> FastAPI:
    app = FastAPI(
        title=PROJECT_NAME,
        version=API_VERSION,
        openapi_url=f"{API_V1_PREFIX}/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8501",
            "http://127.0.0.1:8501",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=API_V1_PREFIX)
    return app


app = create_app()
