import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.shared.db.session import get_db
from shared.shared.exceptions.handlers import setup_exception_handlers

from .config import get_notification_settings
from .routers.notifications import router as notifications_router
from .services.event_consumer import start_subscriber

_subscriber_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _subscriber_task
    settings = get_notification_settings()

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    _subscriber_task = asyncio.create_task(
        start_subscriber(settings.redis_url, session_factory)
    )
    yield

    if _subscriber_task:
        _subscriber_task.cancel()
        try:
            await _subscriber_task
        except asyncio.CancelledError:
            pass
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="MANUTECH — Notification Service",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    setup_exception_handlers(app)

    app.include_router(notifications_router, prefix="/api/v1")

    @app.get("/health", tags=["infra"])
    async def health_check(db: AsyncSession = Depends(get_db)):
        try:
            await db.execute(text("SELECT 1"))
            return {"status": "ok", "service": "notification-service"}
        except Exception:
            return JSONResponse(status_code=503, content={"status": "unavailable"})

    return app


app = create_app()
