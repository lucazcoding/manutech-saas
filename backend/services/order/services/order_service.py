import json
import uuid
from math import ceil

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.auth.dependencies import UserClaims
from shared.shared.db.rls import set_rls_context
from shared.shared.exceptions.handlers import BusinessError
from shared.shared.redis.client import publish_event
from shared.shared.schemas.pagination import PaginatedResponse

from ..config import OrderSettings
from ..repositories.order_repository import OrderRepository
from ..schemas.order import (
    AssignOrderRequest,
    AttachmentResponse,
    AuditLogEntry,
    CreateOrderRequest,
    OrderFilters,
    OrderResponse,
    OrderStats,
    UpdateOrderRequest,
    UpdateOrderStatusRequest,
)
from .state_machine import validate_status_transition

_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}
_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


class OrderService:
    def __init__(self, db: AsyncSession, redis: Redis, current_user: UserClaims) -> None:
        self._db = db
        self._redis = redis
        self._current_user = current_user
        self._repo = OrderRepository(db)

    async def _set_rls(self) -> None:
        await set_rls_context(self._db, self._current_user.id, self._current_user.role)

    async def list_orders(self, filters: OrderFilters) -> PaginatedResponse[OrderResponse]:
        await self._set_rls()
        items, total = await self._repo.list(filters)
        pages = ceil(total / filters.page_size) if total > 0 else 0
        return PaginatedResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            pages=pages,
        )

    async def create_order(self, data: CreateOrderRequest) -> OrderResponse:
        await self._set_rls()

        if data.asset_id is not None:
            asset = await self._repo.get_asset_by_id(data.asset_id)
            if asset is None:
                raise BusinessError("ASSET_NOT_FOUND", 404, "Equipamento não encontrado")
            if asset.status != "active":
                raise BusinessError("ASSET_INACTIVE", 400, "Equipamento inativo não pode ser vinculado a uma OS")

        order = await self._repo.create(data)
        return await self._repo.get_detail(order.id)

    async def get_order(self, order_id: int) -> OrderResponse:
        await self._set_rls()
        detail = await self._repo.get_detail(order_id)
        if detail is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Ordem de serviço não encontrada")
        return detail

    async def update_order(self, order_id: int, data: UpdateOrderRequest) -> OrderResponse:
        await self._set_rls()
        order = await self._repo.get_by_id(order_id)
        if order is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Ordem de serviço não encontrada")
        if order.status in ("completed", "cancelled"):
            raise BusinessError("ORDER_CLOSED", 400, "Operação não permitida em OS encerrada")

        if data.asset_id is not None:
            asset = await self._repo.get_asset_by_id(data.asset_id)
            if asset is None:
                raise BusinessError("ASSET_NOT_FOUND", 404, "Equipamento não encontrado")
            if asset.status != "active":
                raise BusinessError("ASSET_INACTIVE", 400, "Equipamento inativo")

        await self._repo.update(order_id, data)
        return await self._repo.get_detail(order_id)

    async def delete_order(self, order_id: int) -> None:
        await self._set_rls()
        order = await self._repo.get_by_id(order_id)
        if order is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Ordem de serviço não encontrada")
        await self._repo.delete(order_id)

    async def update_status(
        self, order_id: int, data: UpdateOrderStatusRequest
    ) -> OrderResponse:
        await self._set_rls()
        order = await self._repo.get_by_id(order_id)
        if order is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Ordem de serviço não encontrada")

        role = self._current_user.role
        if role == "technician":
            assignment = await self._repo.get_active_assignment(order_id)
            if assignment is None or assignment.technician_id != self._current_user.id:
                raise BusinessError(
                    "NOT_ASSIGNED_TECHNICIAN",
                    403,
                    "Apenas o técnico atribuído pode alterar esta OS",
                )
            if data.status == "completed":
                raise BusinessError(
                    "COMPLETION_REQUIRES_SUPERVISOR",
                    403,
                    "Apenas supervisor ou admin pode concluir uma OS. Use 'Solicitar conclusão' para notificar.",
                )
            if data.status == "cancelled":
                raise BusinessError(
                    "CANCELLATION_REQUIRES_SUPERVISOR",
                    403,
                    "Apenas supervisor ou admin pode cancelar uma OS",
                )
            if data.status != "in_progress":
                raise BusinessError(
                    "TECHNICIAN_TRANSITION_NOT_ALLOWED",
                    403,
                    "Técnicos só podem iniciar uma OS (mover para 'em andamento')",
                )

        validate_status_transition(order.status, data.status)

        if data.status == "cancelled" and not data.reason:
            raise BusinessError(
                "CANCELLATION_REASON_REQUIRED", 400, "Motivo de cancelamento é obrigatório"
            )

        if data.status == "in_progress":
            assignment = await self._repo.get_active_assignment(order_id)
            if assignment is None:
                raise BusinessError(
                    "TECHNICIAN_REQUIRED",
                    400,
                    "É necessário atribuir um técnico antes de iniciar a OS",
                )

        await self._repo.update_status(order_id, data.status)

        await publish_event(
            self._redis,
            "order.status_changed",
            {
                "event": "order.status_changed",
                "payload": {
                    "order_id": order_id,
                    "old_status": order.status,
                    "new_status": data.status,
                    "reason": data.reason,
                },
            },
        )

        return await self._repo.get_detail(order_id)

    async def request_completion(self, order_id: int) -> OrderResponse:
        await self._set_rls()
        order = await self._repo.get_by_id(order_id)
        if order is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Ordem de serviço não encontrada")

        assignment = await self._repo.get_active_assignment(order_id)
        if assignment is None or assignment.technician_id != self._current_user.id:
            raise BusinessError(
                "NOT_ASSIGNED_TECHNICIAN",
                403,
                "Apenas o técnico atribuído pode solicitar a conclusão desta OS",
            )

        if order.status != "in_progress":
            raise BusinessError(
                "INVALID_STATUS_FOR_REQUEST",
                400,
                "Só é possível solicitar a conclusão de uma OS em andamento",
            )

        reviewers = await self._repo.list_users_by_roles(["supervisor", "admin"])
        if not reviewers:
            return await self._repo.get_detail(order_id)

        for reviewer in reviewers:
            await publish_event(
                self._redis,
                "order.completion_requested",
                {
                    "event": "order.completion_requested",
                    "user_id": reviewer.id,
                    "payload": {
                        "order_id": order_id,
                        "order_number": order.order_number,
                        "technician_id": self._current_user.id,
                        "technician_name": self._current_user.name,
                    },
                },
            )

        return await self._repo.get_detail(order_id)

    async def assign_technician(
        self, order_id: int, data: AssignOrderRequest
    ) -> OrderResponse:
        await self._set_rls()
        order = await self._repo.get_by_id(order_id)
        if order is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Ordem de serviço não encontrada")
        if order.status in ("completed", "cancelled"):
            raise BusinessError("ORDER_CLOSED", 400, "Operação não permitida em OS encerrada")

        tech = await self._repo.get_user_by_id(data.technician_id)
        if tech is None:
            raise BusinessError("TECHNICIAN_NOT_FOUND", 404, "Técnico não encontrado")
        if tech.role != "technician":
            raise BusinessError(
                "NOT_A_TECHNICIAN", 422, "Usuário não possui role de técnico"
            )

        await self._repo.assign_technician(order_id, data.technician_id)

        await publish_event(
            self._redis,
            "order.assigned",
            {
                "event": "order.assigned",
                "user_id": data.technician_id,
                "payload": {"order_id": order_id, "technician_id": data.technician_id},
            },
        )

        return await self._repo.get_detail(order_id)

    async def get_stats(self, settings: OrderSettings) -> OrderStats:
        await self._set_rls()
        cache_key = "order:stats"
        cached = await self._redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return OrderStats(**data)

        stats = await self._repo.get_stats()
        await self._redis.set(
            cache_key,
            json.dumps(stats.model_dump()),
            ex=settings.stats_cache_ttl_seconds,
        )
        return stats

    async def get_history(self, order_id: int) -> list[AuditLogEntry]:
        await self._set_rls()
        order = await self._repo.get_by_id(order_id)
        if order is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Ordem de serviço não encontrada")
        return await self._repo.get_history(order_id)

    async def list_orders_by_asset(
        self, asset_id: int, page: int, page_size: int
    ) -> PaginatedResponse[OrderResponse]:
        await self._set_rls()
        items, total = await self._repo.list_by_asset(asset_id, page, page_size)
        pages = ceil(total / page_size) if total > 0 else 0
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def list_attachments(self, order_id: int) -> list[AttachmentResponse]:
        await self._set_rls()
        order = await self._repo.get_by_id(order_id)
        if order is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Ordem de serviço não encontrada")
        return await self._repo.list_attachments(order_id)

    async def upload_attachment(
        self,
        order_id: int,
        filename: str,
        mime_type: str,
        content: bytes,
        storage,
    ) -> AttachmentResponse:
        await self._set_rls()
        order = await self._repo.get_by_id(order_id)
        if order is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Ordem de serviço não encontrada")

        if len(content) > _MAX_FILE_SIZE:
            raise BusinessError("FILE_TOO_LARGE", 413, "Arquivo excede o limite de 20 MB")

        if mime_type not in _ALLOWED_MIME_TYPES:
            raise BusinessError(
                "UNSUPPORTED_MIME_TYPE", 422, f"Tipo MIME não suportado: {mime_type}"
            )

        file_path = f"orders/{order_id}/{uuid.uuid4()}"
        await storage.upload(file_path, content, mime_type)

        attachment = await self._repo.create_attachment(
            order_id=order_id,
            uploaded_by=self._current_user.id,
            file_path=file_path,
            original_name=filename,
            mime_type=mime_type,
            size_bytes=len(content),
        )
        return AttachmentResponse.model_validate(attachment)
