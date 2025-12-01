from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from sqlalchemy import func

from database.lib import Database
from database.models import CartItem, Order, OrderItem, OrderStatus, Customer, Transaction

from .stripe_service import StripeService
from .config import setup_logging

logger = setup_logging()
router = APIRouter()


# ---------- DTOs ----------

class CreateSessionRequest(BaseModel):
    customer_id: str


class CreateSessionResponse(BaseModel):
    session_id: str
    checkout_url: str
    order_id: int


class SessionStatusResponse(BaseModel):
    status: str
    payment_status: str
    order_id: Optional[int] = None


class WebhookResponse(BaseModel):
    received: bool


class ConfigResponse(BaseModel):
    publishable_key: Optional[str]


# ---------- Helpers ----------

async def _get_article_price(session, article_id: int) -> float:
    """
    Obtiene el precio promedio de un artículo desde las transacciones.
    Usa la misma lógica que product_routes.py para consistencia.
    """
    try:
        q = select(func.avg(Transaction.price)).where(Transaction.article_id == article_id)
        result = await session.execute(q)
        avg_price = result.scalar()
        if avg_price is None:
            # Fallback determinístico
            base = 29.99
            return float(base + (article_id % 100))
        return float(avg_price)
    except Exception:
        base = 29.99
        return float(base + (article_id % 100))


# ---------- Endpoints ----------

@router.post("/create-session", response_model=CreateSessionResponse)
async def create_checkout_session(request: CreateSessionRequest):
    """
    Crea una sesión de Stripe Checkout a partir del carrito del usuario.

    1. Obtiene los items del carrito
    2. Crea una Order con status "pending"
    3. Crea la sesión de Stripe Checkout
    4. Retorna la URL para redirigir al usuario
    """
    try:
        async with Database.get_session() as session:
            # Verificar que el cliente existe
            customer = (await session.execute(
                select(Customer).where(Customer.customer_id == request.customer_id)
            )).scalar_one_or_none()

            if not customer:
                raise HTTPException(status_code=404, detail="Cliente no encontrado")

            # Obtener items del carrito
            cart_items = (await session.execute(
                select(CartItem)
                .options(selectinload(CartItem.article))
                .where(
                    CartItem.customer_id == request.customer_id,
                    CartItem.quantity > 0
                )
            )).scalars().all()

            if not cart_items:
                raise HTTPException(status_code=400, detail="El carrito está vacío")

            # Calcular total y preparar line_items para Stripe
            line_items = []
            total_amount = 0.0
            order_items_data = []

            for ci in cart_items:
                if not ci.article:
                    continue

                # Obtener precio real desde las transacciones
                unit_price = await _get_article_price(session, ci.article.article_id)
                unit_price_cents = int(round(unit_price * 100))  # Stripe requiere centavos
                item_total = unit_price * ci.quantity
                total_amount += item_total

                # Item para Stripe
                line_items.append({
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": unit_price_cents,
                        "product_data": {
                            "name": ci.article.prod_name,
                            "description": ci.article.detail_desc[:500] if ci.article.detail_desc else None,
                        },
                    },
                    "quantity": ci.quantity,
                })

                # Datos para OrderItem
                order_items_data.append({
                    "article_id": ci.article_id,
                    "product_name": ci.article.prod_name,
                    "quantity": ci.quantity,
                    "unit_price": unit_price,
                    "total_price": item_total,
                })

            # Crear Order
            order = Order(
                customer_id=request.customer_id,
                status=OrderStatus.PENDING.value,
                total_amount=round(total_amount, 2),
                currency="usd",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(order)
            await session.flush()

            # Crear OrderItems
            for item_data in order_items_data:
                order_item = OrderItem(
                    order_id=order.id,
                    **item_data
                )
                session.add(order_item)

            await session.flush()

            # Crear sesión de Stripe Checkout
            result = StripeService.create_checkout_session(
                order_id=order.id,
                line_items=line_items,
                customer_email=customer.email,
            )

            # Guardar session_id de Stripe en la orden
            order.stripe_checkout_session_id = result.session_id
            await session.commit()

            logger.info(f"Checkout session creada: {result.session_id} para orden {order.id}")

            return CreateSessionResponse(
                session_id=result.session_id,
                checkout_url=result.checkout_url,
                order_id=order.id,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear checkout session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear sesión de pago: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """
    Obtiene el estado de una sesión de checkout.
    Útil para verificar si el pago fue exitoso en la página de success.
    """
    try:
        status = StripeService.get_session_status(session_id)

        # Buscar la orden asociada
        order_id = None
        async with Database.get_session() as session:
            order = (await session.execute(
                select(Order).where(Order.stripe_checkout_session_id == session_id)
            )).scalar_one_or_none()

            if order:
                order_id = order.id

        return SessionStatusResponse(
            status=status.status,
            payment_status=status.payment_status,
            order_id=order_id,
        )

    except Exception as e:
        logger.error(f"Error al obtener estado de sesión: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al verificar estado del pago: {str(e)}"
        )


@router.post("/webhook", response_model=WebhookResponse)
async def stripe_webhook(request: Request):
    """
    Webhook para recibir eventos de Stripe.
    IMPORTANTE: Este endpoint NO tiene autenticación, la seguridad viene de la firma.
    """
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature", "")

        if not signature:
            raise HTTPException(status_code=400, detail="Falta header stripe-signature")

        # Verificar firma
        try:
            event = StripeService.verify_webhook_signature(payload, signature)
        except ValueError as e:
            logger.warning(f"Webhook con firma inválida: {e}")
            raise HTTPException(status_code=400, detail="Firma inválida")

        # Procesar evento
        event_type = event.get("type", "")
        logger.info(f"Webhook recibido: {event_type}")

        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(event["data"]["object"])

        elif event_type == "checkout.session.expired":
            await _handle_checkout_expired(event["data"]["object"])

        return WebhookResponse(received=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_checkout_completed(session_data: dict):
    """Maneja el evento checkout.session.completed."""
    session_id = session_data.get("id")
    payment_intent_id = session_data.get("payment_intent")

    logger.info(f"Procesando pago completado para sesión: {session_id}")

    async with Database.get_session() as session:
        # Buscar la orden
        order = (await session.execute(
            select(Order).where(Order.stripe_checkout_session_id == session_id)
        )).scalar_one_or_none()

        if not order:
            logger.warning(f"Orden no encontrada para sesión: {session_id}")
            return

        # Verificar idempotencia
        if order.status == OrderStatus.PAID.value:
            logger.info(f"Orden {order.id} ya estaba marcada como pagada")
            return

        # Actualizar orden
        order.status = OrderStatus.PAID.value
        order.stripe_payment_intent_id = payment_intent_id
        order.paid_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()

        # Limpiar carrito del usuario
        cart_items = (await session.execute(
            select(CartItem).where(CartItem.customer_id == order.customer_id)
        )).scalars().all()

        for item in cart_items:
            await session.delete(item)

        await session.commit()

        logger.info(f"Orden {order.id} marcada como pagada y carrito limpiado")


async def _handle_checkout_expired(session_data: dict):
    """Maneja el evento checkout.session.expired."""
    session_id = session_data.get("id")

    logger.info(f"Sesión expirada: {session_id}")

    async with Database.get_session() as session:
        order = (await session.execute(
            select(Order).where(Order.stripe_checkout_session_id == session_id)
        )).scalar_one_or_none()

        if not order:
            return

        # Solo cancelar si sigue pendiente
        if order.status == OrderStatus.PENDING.value:
            order.status = OrderStatus.CANCELLED.value
            order.updated_at = datetime.utcnow()
            await session.commit()
            logger.info(f"Orden {order.id} cancelada por expiración")


@router.get("/config", response_model=ConfigResponse)
async def get_stripe_config():
    """Retorna la configuración pública de Stripe para el frontend."""
    return ConfigResponse(
        publishable_key=StripeService.get_publishable_key()
    )
