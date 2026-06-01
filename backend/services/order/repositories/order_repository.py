from datetime import datetime, timezone
from decimal import Decimal
from math import ceil
from typing import Optional

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.order import (
    AuditLog,
    OrderAsset,
    OrderAssignment,
    OrderAttachment,
    OrderUser,
    ServiceOrder,
)
from ..schemas.order import (
    AssignOrderRequest,
    AttachmentResponse,
    AuditLogEntry,
    CreateOrderRequest,
    OrderFilters,
    OrderResponse,
    OrderStats,
    TechnicianSummary,
    AssetSummary,
    UpdateOrderRequest,
)


class OrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _build_order_response(self, order: ServiceOrder) -> OrderResponse:
        """Build enriched OrderResponse with asset and technician summaries."""
        asset = None
        if order.asset_id:
            r = await self._db.execute(
                select(OrderAsset).where(OrderAsset.id == order.asset_id)
            )
            a = r.scalar_one_or_none()
            if a:
                asset = AssetSummary(id=a.id, name=a.name, serial_number=a.serial_number)

        technician = None
        r = await self._db.execute(
            select(OrderAssignment)
            .where(
                and_(
                    OrderAssignment.service_order_id == order.id,
                    OrderAssignment.active.is_(True),
                )
            )
        )
        assignment = r.scalar_one_or_none()
        if assignment:
            r2 = await self._db.execute(
                select(OrderUser).where(OrderUser.id == assignment.technician_id)
            )
            tech = r2.scalar_one_or_none()
            if tech:
                technician = TechnicianSummary(id=tech.id, name=tech.name)

        return OrderResponse(
            id=order.id,
            order_number=order.order_number,
            client_name=order.client_name,
            location=order.location,
            description=order.description,
            status=order.status,
            priority=order.priority,
            total_cost=order.total_cost,
            start_date=order.start_date,
            asset=asset,
            assigned_technician=technician,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    async def list(self, filters: OrderFilters) -> tuple[list[OrderResponse], int]:
        base = select(ServiceOrder)

        if filters.status:
            base = base.where(ServiceOrder.status == filters.status)
        if filters.priority:
            base = base.where(ServiceOrder.priority == filters.priority)
        if filters.client_name:
            base = base.where(ServiceOrder.client_name.ilike(f"%{filters.client_name}%"))
        if filters.order_number:
            base = base.where(ServiceOrder.order_number == filters.order_number)
        if filters.asset_id:
            base = base.where(ServiceOrder.asset_id == filters.asset_id)
        if filters.start_date_from:
            base = base.where(ServiceOrder.start_date >= filters.start_date_from)
        if filters.start_date_to:
            base = base.where(ServiceOrder.start_date <= filters.start_date_to)
        if filters.technician_id:
            active_orders = (
                select(OrderAssignment.service_order_id)
                .where(
                    and_(
                        OrderAssignment.technician_id == filters.technician_id,
                        OrderAssignment.active.is_(True),
                    )
                )
                .scalar_subquery()
            )
            base = base.where(ServiceOrder.id.in_(active_orders))

        count_result = await self._db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        offset = (filters.page - 1) * filters.page_size
        rows = await self._db.execute(
            base.order_by(ServiceOrder.created_at.desc()).offset(offset).limit(filters.page_size)
        )
        orders = list(rows.scalars().all())
        items = [await self._build_order_response(o) for o in orders]
        return items, total

    async def get_by_id(self, order_id: int) -> ServiceOrder | None:
        result = await self._db.execute(
            select(ServiceOrder).where(ServiceOrder.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_detail(self, order_id: int) -> OrderResponse | None:
        order = await self.get_by_id(order_id)
        if order is None:
            return None
        return await self._build_order_response(order)

    async def create(self, data: CreateOrderRequest) -> ServiceOrder:
        order = ServiceOrder(
            client_name=data.client_name,
            location=data.location,
            description=data.description,
            priority=data.priority or "medium",
            start_date=data.start_date,
            asset_id=data.asset_id,
        )
        self._db.add(order)
        await self._db.flush()
        await self._db.refresh(order)
        return order

    async def update(self, order_id: int, data: UpdateOrderRequest) -> ServiceOrder | None:
        changes = {k: v for k, v in data.model_dump().items() if v is not None}
        if changes:
            await self._db.execute(
                update(ServiceOrder)
                .where(ServiceOrder.id == order_id)
                .values(**changes, updated_at=func.now())
            )
            await self._db.flush()
        return await self.get_by_id(order_id)

    async def update_status(self, order_id: int, status: str) -> ServiceOrder | None:
        await self._db.execute(
            update(ServiceOrder)
            .where(ServiceOrder.id == order_id)
            .values(status=status, updated_at=func.now())
        )
        await self._db.flush()
        return await self.get_by_id(order_id)

    async def delete(self, order_id: int) -> None:
        await self._db.execute(delete(ServiceOrder).where(ServiceOrder.id == order_id))
        await self._db.flush()

    async def get_active_assignment(self, order_id: int) -> OrderAssignment | None:
        r = await self._db.execute(
            select(OrderAssignment).where(
                and_(
                    OrderAssignment.service_order_id == order_id,
                    OrderAssignment.active.is_(True),
                )
            )
        )
        return r.scalar_one_or_none()

    async def assign_technician(self, order_id: int, technician_id: int) -> None:
        existing = await self.get_active_assignment(order_id)
        if existing:
            await self._db.execute(
                update(OrderAssignment)
                .where(OrderAssignment.id == existing.id)
                .values(active=False, unassigned_at=func.now())
            )
            await self._db.flush()

        assignment = OrderAssignment(
            service_order_id=order_id,
            technician_id=technician_id,
            assigned_at=datetime.now(timezone.utc),
        )
        self._db.add(assignment)
        await self._db.flush()

    async def get_stats(self) -> OrderStats:
        status_result = await self._db.execute(
            select(ServiceOrder.status, func.count(ServiceOrder.id))
            .group_by(ServiceOrder.status)
        )
        priority_result = await self._db.execute(
            select(ServiceOrder.priority, func.count(ServiceOrder.id))
            .group_by(ServiceOrder.priority)
        )

        by_status = {row[0]: row[1] for row in status_result.all()}
        by_priority = {row[0]: row[1] for row in priority_result.all()}
        total = sum(by_status.values())

        return OrderStats(total=total, by_status=by_status, by_priority=by_priority)

    async def get_history(self, order_id: int) -> list[AuditLogEntry]:
        result = await self._db.execute(
            select(AuditLog)
            .where(
                and_(
                    AuditLog.table_name == "service_orders",
                    AuditLog.record_id == order_id,
                )
            )
            .order_by(AuditLog.created_at.desc())
        )
        return [AuditLogEntry.model_validate(row) for row in result.scalars().all()]

    async def list_by_asset(self, asset_id: int, page: int, page_size: int) -> tuple[list[OrderResponse], int]:
        base = select(ServiceOrder).where(ServiceOrder.asset_id == asset_id)

        count_result = await self._db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        rows = await self._db.execute(
            base.order_by(ServiceOrder.created_at.desc()).offset(offset).limit(page_size)
        )
        orders = list(rows.scalars().all())
        items = [await self._build_order_response(o) for o in orders]
        return items, total

    async def list_attachments(self, order_id: int) -> list[AttachmentResponse]:
        result = await self._db.execute(
            select(OrderAttachment)
            .where(OrderAttachment.service_order_id == order_id)
            .order_by(OrderAttachment.created_at.desc())
        )
        return [AttachmentResponse.model_validate(a) for a in result.scalars().all()]

    async def create_attachment(
        self,
        order_id: int,
        uploaded_by: int,
        file_path: str,
        original_name: str,
        mime_type: str,
        size_bytes: int,
    ) -> OrderAttachment:
        attachment = OrderAttachment(
            service_order_id=order_id,
            uploaded_by=uploaded_by,
            file_path=file_path,
            original_name=original_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )
        self._db.add(attachment)
        await self._db.flush()
        await self._db.refresh(attachment)
        return attachment

    async def get_user_by_id(self, user_id: int) -> OrderUser | None:
        result = await self._db.execute(
            select(OrderUser).where(OrderUser.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_asset_by_id(self, asset_id: int) -> OrderAsset | None:
        result = await self._db.execute(
            select(OrderAsset).where(OrderAsset.id == asset_id)
        )
        return result.scalar_one_or_none()
