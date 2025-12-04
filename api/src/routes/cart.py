from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database.lib import Database
from database.models import CartItem, Article

router = APIRouter()


# ---------- DTOs ----------

class CartItemDTO(BaseModel):
    id: int
    article_id: int
    quantity: int
    added_at: datetime
    article_name: Optional[str] = None
    article_price: Optional[float] = None
    article_image: Optional[str] = None


class CartSummaryDTO(BaseModel):
    customer_id: str
    items: List[CartItemDTO]
    total_items: int
    total_quantity: int
    total_amount: float


# ---------- helpers ----------

def _image_url(article_id: int) -> str | None:
    # No hay fallback - el frontend mostrará un placeholder
    return None


def _mock_price(article_id: int) -> float:
    # Elige una de estas opciones:

    # Opción A: precio fijo (como se ve en tu UI)
    return 0.01

    # Opción B: precio determinista "bonito"
    # return round(19.99 + (article_id % 80) * 0.5, 2)



def _to_dto(ci: CartItem) -> CartItemDTO:
    name = None
    price = None
    img = None
    if ci.article:
        name = getattr(ci.article, "prod_name", None)
        price = _mock_price(ci.article.article_id)
        img = _image_url(ci.article.article_id)
    return CartItemDTO(
        id=ci.id,
        article_id=ci.article_id,
        quantity=ci.quantity,
        added_at=ci.added_at,
        article_name=name,
        article_price=price,
        article_image=img,
    )


# ---------- endpoints ----------

@router.post("/add", response_model=CartItemDTO, status_code=201)
async def add_to_cart(
    customer_id: str = Query(..., description="ID del cliente"),
    article_id: int = Query(..., description="Article ID del producto"),
    quantity: int = Query(1, ge=1),
):
    """
    POST /api/v1/cart/add?customer_id=&article_id=&quantity=
    Suma cantidad si el item ya existe.
    """
    try:
        async with Database.get_session() as session:
            # Verificar artículo
            art = (await session.execute(
                select(Article).where(Article.article_id == article_id)
            )).scalar_one_or_none()
            if not art:
                raise HTTPException(status_code=404, detail="Artículo no encontrado")

            # Buscar ítem
            existing = (await session.execute(
                select(CartItem)
                .options(selectinload(CartItem.article))
                .where(CartItem.customer_id == customer_id, CartItem.article_id == article_id)
            )).scalar_one_or_none()

            if existing:
                existing.quantity += quantity
                await session.flush()
                await session.commit()  # <-- COMMIT
                # refrescar
                existing = (await session.execute(
                    select(CartItem)
                    .options(selectinload(CartItem.article))
                    .where(CartItem.id == existing.id)
                )).scalar_one()
                return _to_dto(existing)

            # Crear nuevo
            item = CartItem(
                customer_id=customer_id,
                article_id=article_id,
                quantity=quantity,
                added_at=datetime.utcnow(),
            )
            session.add(item)
            await session.flush()
            await session.commit()  # <-- COMMIT

            created = (await session.execute(
                select(CartItem)
                .options(selectinload(CartItem.article))
                .where(CartItem.id == item.id)
            )).scalar_one()

            return _to_dto(created)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al agregar producto al carrito: {e}"
        )


@router.put("/item/{customer_id}/{article_id}", response_model=dict)
async def set_item_quantity(
    customer_id: str,
    article_id: int,
    quantity: int = Query(..., ge=0, description="Cantidad final (0 elimina el ítem)"),
):
    """
    Fija la cantidad exacta. Si quantity == 0, elimina el ítem y devuelve {ok: True}.
    """
    try:
        async with Database.get_session() as session:
            item = (await session.execute(
                select(CartItem)
                .options(selectinload(CartItem.article))
                .where(CartItem.customer_id == customer_id, CartItem.article_id == article_id)
            )).scalar_one_or_none()

            if not item:
                if quantity == 0:
                    return {"ok": True}  # ya no está, estado idempotente
                # crear si no existe y quantity > 0
                art = (await session.execute(
                    select(Article).where(Article.article_id == article_id)
                )).scalar_one_or_none()
                if not art:
                    raise HTTPException(status_code=404, detail="Artículo no encontrado")
                new_item = CartItem(
                    customer_id=customer_id,
                    article_id=article_id,
                    quantity=quantity,
                    added_at=datetime.utcnow(),
                )
                session.add(new_item)
                await session.commit()
                return {"ok": True}

            # existe
            if quantity == 0:
                session.delete(item)
                await session.commit()
                return {"ok": True}

            item.quantity = quantity
            await session.flush()
            await session.commit()
            return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar cantidad: {e}")



@router.delete("/remove", response_model=dict)
async def remove_from_cart(
    customer_id: str = Query(...),
    article_id: int = Query(...),
    quantity: int = Query(1, ge=1),
):
    """
    DELETE /api/v1/cart/remove?customer_id=&article_id=&quantity=
    Resta 'quantity'. Si llega a 0 o menos, elimina el ítem.
    """
    try:
        async with Database.get_session() as session:
            item = (await session.execute(
                select(CartItem)
                .where(CartItem.customer_id == customer_id, CartItem.article_id == article_id)
            )).scalar_one_or_none()

            if not item:
                raise HTTPException(status_code=404, detail="Item no encontrado")

            item.quantity -= quantity
            if item.quantity <= 0:
                session.delete(item)  # sync
            else:
                await session.flush()

            await session.commit()  # <-- COMMIT
            return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar del carrito: {e}")


@router.delete("/clear/{customer_id}", response_model=dict)
async def clear_cart(customer_id: str):
    """
    DELETE /api/v1/cart/clear/{customer_id}
    Elimina todos los ítems del carrito.
    """
    try:
        async with Database.get_session() as session:
            items = (await session.execute(
                select(CartItem).where(CartItem.customer_id == customer_id)
            )).scalars().all()

            if not items:
                return {"ok": True}

            for it in items:
                session.delete(it)

            await session.commit()  # <-- COMMIT
            return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al vaciar el carrito: {e}")


@router.get("/{customer_id}", response_model=CartSummaryDTO)
async def get_cart(customer_id: str):
    try:
        async with Database.get_session() as session:
            items = (await session.execute(
                select(CartItem)
                .options(selectinload(CartItem.article))
                .where(
                    CartItem.customer_id == customer_id,
                    CartItem.quantity > 0        # 👈 filtra los ceros
                )
                .order_by(CartItem.added_at.desc())
            )).scalars().all()

            dto = [_to_dto(x) for x in items]
            total_items = len(dto)
            total_qty = sum(x.quantity for x in dto)
            total_amount = round(sum((x.article_price or 0.0) * x.quantity for x in dto), 2)

            return CartSummaryDTO(
                customer_id=customer_id,
                items=dto,
                total_items=total_items,
                total_quantity=total_qty,
                total_amount=total_amount,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el carrito: {e}")



@router.get("/count/{customer_id}", response_model=dict)
async def get_cart_count(customer_id: str):
    try:
        async with Database.get_session() as session:
            count = (await session.execute(
                select(func.count(CartItem.id)).where(CartItem.customer_id == customer_id)
            )).scalar() or 0
            return {"total_items": int(count)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el conteo: {e}")
