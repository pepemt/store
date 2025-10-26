"""
Funciones para manejar operaciones del carrito de compras.
"""

from typing import List, Optional
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload
from database.lib import Database
from database.models import CartItem, Article, Customer


class CartService:
    """Servicio para manejar operaciones del carrito de compras."""
    
    @staticmethod
    async def add_to_cart(customer_id: str, article_id: int, quantity: int = 1) -> CartItem:
        """
        Agrega un artículo al carrito del usuario.
        Si el artículo ya existe, actualiza la cantidad.
        """
        async with Database.get_session() as session:
            # Verificar si el artículo ya está en el carrito
            stmt = select(CartItem).where(
                CartItem.customer_id == customer_id,
                CartItem.article_id == article_id,
                CartItem.is_active == True
            )
            existing_item = await session.scalar(stmt)
            
            if existing_item:
                # Actualizar cantidad existente
                existing_item.quantity += quantity
                await session.commit()
                await session.refresh(existing_item)
                return existing_item
            else:
                # Crear nuevo item en el carrito
                new_item = CartItem(
                    customer_id=customer_id,
                    article_id=article_id,
                    quantity=quantity
                )
                session.add(new_item)
                await session.commit()
                await session.refresh(new_item)
                return new_item
    
    @staticmethod
    async def get_cart_items(customer_id: str) -> List[CartItem]:
        """Obtiene todos los artículos activos del carrito de un usuario."""
        async with Database.get_session() as session:
            stmt = (
                select(CartItem)
                .options(selectinload(CartItem.article))
                .where(
                    CartItem.customer_id == customer_id,
                    CartItem.is_active == True
                )
                .order_by(CartItem.added_at.desc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()
    
    @staticmethod
    async def update_cart_item_quantity(customer_id: str, article_id: int, quantity: int) -> bool:
        """Actualiza la cantidad de un artículo en el carrito."""
        async with Database.get_session() as session:
            if quantity <= 0:
                # Si la cantidad es 0 o negativa, eliminar el item
                return await CartService.remove_from_cart(customer_id, article_id)
            
            stmt = (
                update(CartItem)
                .where(
                    CartItem.customer_id == customer_id,
                    CartItem.article_id == article_id,
                    CartItem.is_active == True
                )
                .values(quantity=quantity)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    
    @staticmethod
    async def remove_from_cart(customer_id: str, article_id: int) -> bool:
        """Elimina un artículo específico del carrito."""
        async with Database.get_session() as session:
            stmt = (
                update(CartItem)
                .where(
                    CartItem.customer_id == customer_id,
                    CartItem.article_id == article_id,
                    CartItem.is_active == True
                )
                .values(is_active=False)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    
    @staticmethod
    async def clear_cart(customer_id: str) -> bool:
        """Vacía completamente el carrito de un usuario."""
        async with Database.get_session() as session:
            stmt = (
                update(CartItem)
                .where(
                    CartItem.customer_id == customer_id,
                    CartItem.is_active == True
                )
                .values(is_active=False)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    
    @staticmethod
    async def get_cart_total(customer_id: str) -> float:
        """Calcula el total del carrito de un usuario."""
        cart_items = await CartService.get_cart_items(customer_id)
        total = 0.0
        
        for item in cart_items:
            # Necesitamos obtener el precio del artículo desde las transacciones
            # o agregar un campo de precio al modelo Article
            # Por ahora, usaremos un precio base de ejemplo
            total += item.quantity * 10.0  # Precio base de ejemplo
        
        return total
    
    @staticmethod
    async def get_cart_item_count(customer_id: str) -> int:
        """Obtiene el número total de artículos en el carrito."""
        cart_items = await CartService.get_cart_items(customer_id)
        return sum(item.quantity for item in cart_items)