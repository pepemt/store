"""
Rutas de la API para el manejo del carrito de compras.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field
from datetime import datetime

from database.models import Customer
from database.cart_service import CartService


router = APIRouter()


class CartItemRequest(BaseModel):
    """Modelo para agregar/actualizar items en el carrito."""
    customer_id: str = Field(..., description="ID del cliente")
    article_id: int = Field(..., description="ID del artículo")
    quantity: int = Field(1, ge=1, description="Cantidad del producto (mínimo 1)")


class CartItemResponse(BaseModel):
    """Modelo de respuesta para items del carrito."""
    id: int
    article_id: int
    quantity: int
    added_at: datetime
    article_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class CartSummary(BaseModel):
    """Resumen del carrito de compras."""
    total_items: int
    total_quantity: int
    estimated_total: float
    items: List[CartItemResponse]


@router.post("/add", response_model=CartItemResponse)
async def add_to_cart(item: CartItemRequest):
    """Agrega un artículo al carrito del usuario especificado."""
    try:
        cart_item = await CartService.add_to_cart(
            customer_id=item.customer_id,
            article_id=item.article_id,
            quantity=item.quantity
        )
        
        return CartItemResponse(
            id=cart_item.id,
            article_id=cart_item.article_id,
            quantity=cart_item.quantity,
            added_at=cart_item.added_at,
            article_name=cart_item.article.prod_name if cart_item.article else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al agregar producto al carrito: {str(e)}"
        )


@router.get("/{customer_id}", response_model=CartSummary)
async def get_cart(customer_id: str):
    """Obtiene el carrito completo del usuario especificado."""
    try:
        cart_items = await CartService.get_cart_items(customer_id)
        total_quantity = await CartService.get_cart_item_count(customer_id)
        estimated_total = await CartService.get_cart_total(customer_id)
        
        items_response = [
            CartItemResponse(
                id=item.id,
                article_id=item.article_id,
                quantity=item.quantity,
                added_at=item.added_at,
                article_name=item.article.prod_name if item.article else None
            )
            for item in cart_items
        ]
        
        return CartSummary(
            total_items=len(cart_items),
            total_quantity=total_quantity,
            estimated_total=estimated_total,
            items=items_response
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el carrito: {str(e)}"
        )


@router.put("/item/{customer_id}/{article_id}", response_model=dict)
async def update_cart_item(
    customer_id: str,
    article_id: int,
    quantity: int = Query(..., ge=0, description="Nueva cantidad (0 para eliminar)")
):
    """Actualiza la cantidad de un artículo específico en el carrito."""
    try:
        success = await CartService.update_cart_item_quantity(
            customer_id=customer_id,
            article_id=article_id,
            quantity=quantity
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artículo no encontrado en el carrito"
            )
        
        action = "eliminado" if quantity == 0 else "actualizado"
        return {"message": f"Artículo {action} correctamente", "article_id": article_id}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el carrito: {str(e)}"
        )


@router.delete("/item/{customer_id}/{article_id}", response_model=dict)
async def remove_from_cart(
    customer_id: str,
    article_id: int
):
    """Elimina un artículo específico del carrito."""
    try:
        success = await CartService.remove_from_cart(
            customer_id=customer_id,
            article_id=article_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artículo no encontrado en el carrito"
            )
        
        return {"message": "Artículo eliminado del carrito", "article_id": article_id}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar del carrito: {str(e)}"
        )


@router.delete("/clear/{customer_id}", response_model=dict)
async def clear_cart(customer_id: str):
    """Vacía completamente el carrito del usuario especificado."""
    try:
        success = await CartService.clear_cart(customer_id)
        
        if not success:
            return {"message": "El carrito ya estaba vacío"}
        
        return {"message": "Carrito vaciado correctamente"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al vaciar el carrito: {str(e)}"
        )


@router.get("/count/{customer_id}", response_model=dict)
async def get_cart_count(customer_id: str):
    """Obtiene el número total de artículos en el carrito."""
    try:
        count = await CartService.get_cart_item_count(customer_id)
        return {"total_items": count}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el conteo del carrito: {str(e)}"
        )