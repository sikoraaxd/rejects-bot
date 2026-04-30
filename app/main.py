from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import API_V1_PREFIX, API_VERSION, PROJECT_NAME


def create_app() -> FastAPI:
    app = FastAPI(
        title=PROJECT_NAME,
        version=API_VERSION,
        openapi_url=f"{API_V1_PREFIX}/openapi.json",
    )
    app.include_router(api_router, prefix=API_V1_PREFIX)
    return app


app = create_app()
