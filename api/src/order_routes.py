from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database.lib import Database
from database.models import Order, OrderItem

from .config import setup_logging

logger = setup_logging()
router = APIRouter()


# ---------- DTOs ----------

class OrderItemDTO(BaseModel):
    id: int
    article_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_price: float


class OrderDTO(BaseModel):
    id: int
    status: str
    currency: str
    total_amount: float
    items_count: int
    created_at: datetime
    paid_at: Optional[datetime] = None


class OrderDetailDTO(BaseModel):
    id: int
    status: str
    currency: str
    total_amount: float
    stripe_payment_intent_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime] = None
    items: List[OrderItemDTO]


class OrderListResponse(BaseModel):
    orders: List[OrderDTO]
    total: int
    limit: int
    offset: int


# ---------- Endpoints ----------

@router.get("/{customer_id}", response_model=OrderListResponse)
async def get_orders(
    customer_id: str,
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Lista las órdenes de un cliente.

    GET /api/v1/orders/{customer_id}?status=paid&limit=20&offset=0
    """
    try:
        async with Database.get_session() as session:
            # Query base
            query = select(Order).where(Order.customer_id == customer_id)
            count_query = select(func.count(Order.id)).where(Order.customer_id == customer_id)

            # Filtro por status
            if status:
                query = query.where(Order.status == status)
                count_query = count_query.where(Order.status == status)

            # Total
            total = (await session.execute(count_query)).scalar() or 0

            # Obtener órdenes con paginación
            orders = (await session.execute(
                query
                .options(selectinload(Order.items))
                .order_by(Order.created_at.desc())
                .limit(limit)
                .offset(offset)
            )).scalars().all()

            order_dtos = []
            for order in orders:
                order_dtos.append(OrderDTO(
                    id=order.id,
                    status=order.status,
                    currency=order.currency,
                    total_amount=order.total_amount,
                    items_count=len(order.items),
                    created_at=order.created_at,
                    paid_at=order.paid_at,
                ))

            return OrderListResponse(
                orders=order_dtos,
                total=total,
                limit=limit,
                offset=offset,
            )

    except Exception as e:
        logger.error(f"Error al obtener órdenes: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener historial de pedidos: {str(e)}"
        )


@router.get("/{customer_id}/{order_id}", response_model=OrderDetailDTO)
async def get_order_detail(customer_id: str, order_id: int):
    """
    Obtiene el detalle de una orden específica.

    GET /api/v1/orders/{customer_id}/{order_id}
    """
    try:
        async with Database.get_session() as session:
            order = (await session.execute(
                select(Order)
                .options(selectinload(Order.items))
                .where(
                    Order.id == order_id,
                    Order.customer_id == customer_id
                )
            )).scalar_one_or_none()

            if not order:
                raise HTTPException(
                    status_code=404,
                    detail="Orden no encontrada"
                )

            items_dto = [
                OrderItemDTO(
                    id=item.id,
                    article_id=item.article_id,
                    product_name=item.product_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                )
                for item in order.items
            ]

            return OrderDetailDTO(
                id=order.id,
                status=order.status,
                currency=order.currency,
                total_amount=order.total_amount,
                stripe_payment_intent_id=order.stripe_payment_intent_id,
                created_at=order.created_at,
                updated_at=order.updated_at,
                paid_at=order.paid_at,
                items=items_dto,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener detalle de orden: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener detalle del pedido: {str(e)}"
        )
