from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.db.session import get_db
from shared.shared.exceptions.handlers import setup_exception_handlers

from .routers import assets as assets_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="MANUTECH — Asset Service",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    setup_exception_handlers(app)

    app.include_router(assets_router.router, prefix="/api/v1")

    @app.get("/health", tags=["infra"])
    async def health_check(db: AsyncSession = Depends(get_db)):
        try:
            await db.execute(text("SELECT 1"))
            return {"status": "ok", "service": "asset-service"}
        except Exception:
            return JSONResponse(status_code=503, content={"status": "unavailable"})

    return app


app = create_app()
