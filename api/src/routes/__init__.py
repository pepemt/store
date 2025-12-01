"""
API Routes Package
Exports all routers for use in main.py
"""

from .auth import router as auth_router
from .products import router as product_router
from .cart import router as cart_router
from .orders import router as order_router
from .checkout import router as checkout_router
from .chat import router as chat_router
from .images import router as image_router
from .recommendations import router as recommendations_router

__all__ = [
    "auth_router",
    "product_router",
    "cart_router",
    "order_router",
    "checkout_router",
    "chat_router",
    "image_router",
    "recommendations_router",
]
