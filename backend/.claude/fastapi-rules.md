# FastAPI — Padrões de Código

## Stack

```
FastAPI           # framework web
Pydantic v2       # validação e serialização
SQLAlchemy 2      # ORM async
asyncpg           # driver PostgreSQL async
Alembic           # migrations
```

---

## Estrutura de um Router (Controller)

O router é **fino**: valida input, verifica permissão, chama service, retorna response.  
Sem lógica de negócio. Sem acesso ao banco. Sem SQL.

```python
# services/order/routers/orders.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from shared.auth.dependencies import get_current_user, require_roles
from shared.db.session import get_db
from shared.redis.client import get_redis
from shared.schemas.pagination import PaginatedResponse

from ..schemas.order import OrderListItem, OrderDetail, CreateOrderRequest
from ..schemas.filters import OrderFilters
from ..services.order_service import OrderService
from ..dependencies import get_order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get(
    "",
    response_model=PaginatedResponse[OrderListItem],
    summary="Lista ordens de serviço",
)
async def list_orders(
    filters: OrderFilters = Depends(),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    _=Depends(require_roles(["admin", "supervisor", "technician"])),
):
    service = OrderService(db, redis)
    return await service.list_orders(filters, current_user)


@router.post(
    "",
    response_model=OrderDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Cria nova ordem de serviço",
)
async def create_order(
    body: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    _=Depends(require_roles(["supervisor", "attendant"])),
):
    service = OrderService(db, redis)
    return await service.create_order(body, current_user)
```

---

## Estrutura de um Service (Caso de Uso)

O service **concentra toda a lógica de negócio**. Não conhece FastAPI.

```python
# services/order/services/order_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from shared.db.rls import set_rls_context
from shared.exceptions.business import BusinessError
from shared.schemas.pagination import PaginatedResponse

from ..repositories.order_repository import OrderRepository
from ..repositories.asset_repository import AssetRepository
from ..schemas.order import OrderListItem, OrderDetail, CreateOrderRequest
from ..schemas.filters import OrderFilters


class OrderService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self._db = db
        self._redis = redis
        self._order_repo = OrderRepository(db)
        self._asset_repo = AssetRepository(db)

    async def create_order(self, body: CreateOrderRequest, current_user) -> OrderDetail:
        await set_rls_context(self._db, current_user.id, current_user.role)

        # Validação de negócio: asset_id opcional, mas se informado deve existir e estar ativo
        if body.asset_id is not None:
            asset = await self._asset_repo.get_by_id(body.asset_id)
            if asset is None:
                raise BusinessError("ASSET_NOT_FOUND", 404, "Equipamento não encontrado")
            if asset.status != "active":
                raise BusinessError("ASSET_INACTIVE", 400, "Equipamento inativo não pode ser vinculado a uma OS")

        order = await self._order_repo.create(body, created_by=current_user.id)
        return await self._order_repo.get_detail(order.id)

    async def list_orders(self, filters: OrderFilters, current_user) -> PaginatedResponse[OrderListItem]:
        await set_rls_context(self._db, current_user.id, current_user.role)
        return await self._order_repo.list(filters)
```

---

## Estrutura de um Repository (Acesso a Dados)

O repository **só acessa o banco**. Sem lógica de negócio.

```python
# services/order/repositories/order_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from math import ceil

from ..models.order import ServiceOrder, OrderAssignment
from ..models.asset import Asset
from ..models.user import User
from ..schemas.order import CreateOrderRequest, OrderListItem
from ..schemas.filters import OrderFilters


class OrderRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, data: CreateOrderRequest, created_by: int) -> ServiceOrder:
        order = ServiceOrder(
            client_name=data.client_name,
            location=data.location,
            description=data.description,
            priority=data.priority or "medium",
            start_date=data.start_date,
            asset_id=data.asset_id,
        )
        self._db.add(order)
        await self._db.flush()  # flush para gerar o ID sem commitar
        await self._db.refresh(order)
        return order

    async def get_detail(self, order_id: int) -> OrderListItem | None:
        result = await self._db.execute(
            select(
                ServiceOrder.id,
                ServiceOrder.order_number,
                ServiceOrder.client_name,
                ServiceOrder.location,
                ServiceOrder.description,
                ServiceOrder.status,
                ServiceOrder.priority,
                ServiceOrder.total_cost,
                ServiceOrder.start_date,
                ServiceOrder.asset_id,
                ServiceOrder.created_at,
                ServiceOrder.updated_at,
            ).where(ServiceOrder.id == order_id)
        )
        return result.one_or_none()
```

---

## Schemas Pydantic v2

```python
# services/order/schemas/order.py
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional


class AssetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    serial_number: Optional[str] = None


class TechnicianSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class OrderListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: int
    client_name: str
    location: str
    status: str
    priority: str
    total_cost: Decimal
    start_date: Optional[date] = None
    asset: Optional[AssetSummary] = None
    assigned_technician: Optional[TechnicianSummary] = None
    created_at: datetime
    updated_at: datetime


class CreateOrderRequest(BaseModel):
    client_name: str
    location: str
    description: Optional[str] = None
    priority: Optional[str] = "medium"
    start_date: Optional[date] = None
    asset_id: Optional[int] = None

    @field_validator("client_name", "location")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo não pode ser vazio")
        return v.strip()
```

---

## Exception Handlers

```python
# shared/exceptions/handlers.py
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class BusinessError(Exception):
    def __init__(self, code: str, status_code: int, detail: str, field: str | None = None):
        self.code = code
        self.status_code = status_code
        self.detail = detail
        self.field = field


def setup_exception_handlers(app):
    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError):
        body = {"detail": exc.detail, "code": exc.code}
        if exc.field:
            body["field"] = exc.field
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"] if loc != "body")
        return JSONResponse(
            status_code=422,
            content={
                "detail": first_error["msg"],
                "code": "VALIDATION_ERROR",
                "field": field,
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        # Log interno — nunca expor stack trace ao cliente
        import logging
        logging.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno do servidor", "code": "INTERNAL_ERROR"},
        )
```

---

## Filtros com Query Params

```python
# services/order/schemas/filters.py
from fastapi import Query
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class OrderFilters:
    status: Optional[str] = Query(default=None)
    priority: Optional[str] = Query(default=None)
    technician_id: Optional[int] = Query(default=None)
    client_name: Optional[str] = Query(default=None)
    order_number: Optional[int] = Query(default=None)
    asset_id: Optional[int] = Query(default=None)
    start_date_from: Optional[date] = Query(default=None)
    start_date_to: Optional[date] = Query(default=None)
    page: int = Query(default=1, ge=1)
    page_size: int = Query(default=20, ge=1, le=100)
```

---

## Health Check (obrigatório em cada serviço)

```python
# Em cada main.py
@app.get("/health", tags=["infra"])
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "service": "order-service"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
```

---

## App Factory (main.py)

```python
# services/order/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

from shared.exceptions.handlers import setup_exception_handlers
from .routers import orders, stats, attachments


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown


def create_app() -> FastAPI:
    app = FastAPI(
        title="MANUTECH — Order Service",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    setup_exception_handlers(app)

    app.include_router(orders.router, prefix="/api/v1")
    app.include_router(stats.router, prefix="/api/v1")
    app.include_router(attachments.router, prefix="/api/v1")

    return app


app = create_app()
```
