"""
Rutas de la API para el manejo de productos.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database.lib import Database
from database.models import Article, Transaction


router = APIRouter()


class ProductResponse(BaseModel):
    """Modelo de respuesta para productos."""
    id: int
    name: str
    description: Optional[str]
    category: str
    department: str
    product_group: str
    color_group: str
    # Campos calculados
    price: float = 0.0
    stock: int = 100
    rating: float = 4.0
    images: List[str] = []
    
    class Config:
        populate_by_name = True
        from_attributes = True


class ProductListResponse(BaseModel):
    """Respuesta para lista de productos."""
    products: List[ProductResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class CategoryResponse(BaseModel):
    """Respuesta para categorías."""
    categories: List[str]


@router.get("/", response_model=ProductListResponse)
async def get_products(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Productos por página"),
    search: Optional[str] = Query(None, description="Término de búsqueda"),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    department: Optional[str] = Query(None, description="Filtrar por departamento")
):
    """Obtiene lista de productos con paginación y filtros."""
    try:
        async with Database.get_session() as session:
            # Query base
            query = select(Article)
            count_query = select(func.count(Article.article_id))
            
            # Aplicar filtros
            if search:
                search_term = f"%{search.lower()}%"
                query = query.where(
                    (func.lower(Article.prod_name).contains(search_term)) |
                    (func.lower(Article.detail_desc).contains(search_term)) |
                    (func.lower(Article.product_type_name).contains(search_term))
                )
                count_query = count_query.where(
                    (func.lower(Article.prod_name).contains(search_term)) |
                    (func.lower(Article.detail_desc).contains(search_term)) |
                    (func.lower(Article.product_type_name).contains(search_term))
                )
            
            if category:
                query = query.where(Article.product_type_name == category)
                count_query = count_query.where(Article.product_type_name == category)
                
            if department:
                query = query.where(Article.department_name == department)
                count_query = count_query.where(Article.department_name == department)
            
            # Obtener total de elementos
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0
            
            # Aplicar paginación
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Ejecutar query
            result = await session.execute(query)
            articles = result.scalars().all()
            
            # Convertir a response models
            products = []
            for article in articles:
                # Calcular precio promedio desde transacciones (simplificado)
                price = await _get_average_price(session, article.article_id)
                
                product = ProductResponse(
                    id=article.article_id,
                    name=article.prod_name,
                    description=article.detail_desc,
                    category=article.product_type_name,
                    department=article.department_name,
                    product_group=article.product_group_name,
                    color_group=article.colour_group_name,
                    price=price,
                    stock=100,  # Mock
                    rating=4.0 + (article.article_id % 10) / 10,  # Rating variado
                    images=[f"https://picsum.photos/seed/{article.article_id}/800/600"]
                )
                products.append(product)
            
            total_pages = (total + per_page - 1) // per_page
            
            return ProductListResponse(
                products=products,
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener productos: {str(e)}"
        )


@router.get("/search", response_model=ProductListResponse)
async def search_products(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    limit: int = Query(20, ge=1, le=100, description="Límite de resultados")
):
    """Búsqueda rápida de productos."""
    try:
        async with Database.get_session() as session:
            search_term = f"%{q.lower()}%"
            
            query = select(Article).where(
                (func.lower(Article.prod_name).contains(search_term)) |
                (func.lower(Article.detail_desc).contains(search_term)) |
                (func.lower(Article.product_type_name).contains(search_term)) |
                (func.lower(Article.product_group_name).contains(search_term))
            ).limit(limit)
            
            result = await session.execute(query)
            articles = result.scalars().all()
            
            products = []
            for article in articles:
                price = await _get_average_price(session, article.article_id)
                
                product = ProductResponse(
                    id=article.article_id,
                    name=article.prod_name,
                    description=article.detail_desc,
                    category=article.product_type_name,
                    department=article.department_name,
                    product_group=article.product_group_name,
                    color_group=article.colour_group_name,
                    price=price,
                    stock=100,
                    rating=4.0 + (article.article_id % 10) / 10,
                    images=[f"https://picsum.photos/seed/{article.article_id}/800/600"]
                )
                products.append(product)
            
            return ProductListResponse(
                products=products,
                total=len(products),
                page=1,
                per_page=limit,
                total_pages=1
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en búsqueda: {str(e)}"
        )


@router.get("/categories", response_model=CategoryResponse)
async def get_categories():
    """Obtiene todas las categorías disponibles."""
    try:
        async with Database.get_session() as session:
            query = select(Article.product_type_name).distinct().order_by(Article.product_type_name)
            result = await session.execute(query)
            categories = [row[0] for row in result.fetchall()]
            
            return CategoryResponse(categories=categories)
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener categorías: {str(e)}"
        )


@router.get("/departments", response_model=CategoryResponse)
async def get_departments():
    """Obtiene todos los departamentos disponibles."""
    try:
        async with Database.get_session() as session:
            query = select(Article.department_name).distinct().order_by(Article.department_name)
            result = await session.execute(query)
            departments = [row[0] for row in result.fetchall()]
            
            return CategoryResponse(categories=departments)
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener departamentos: {str(e)}"
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product_by_id(product_id: int):
    """Obtiene un producto específico por ID."""
    try:
        async with Database.get_session() as session:
            query = select(Article).where(Article.article_id == product_id)
            result = await session.execute(query)
            article = result.scalar_one_or_none()
            
            if not article:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Producto no encontrado"
                )
            
            price = await _get_average_price(session, article.article_id)
            
            product = ProductResponse(
                id=article.article_id,
                name=article.prod_name,
                description=article.detail_desc,
                category=article.product_type_name,
                department=article.department_name,
                product_group=article.product_group_name,
                color_group=article.colour_group_name,
                price=price,
                stock=100,
                rating=4.0 + (article.article_id % 10) / 10,
                images=[f"https://picsum.photos/seed/{article.article_id}/800/600"]
            )
            
            return product
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener producto: {str(e)}"
        )


async def _get_average_price(session, article_id: int) -> float:
    """Calcula el precio promedio de un artículo desde las transacciones."""
    try:
        query = select(func.avg(Transaction.price)).where(Transaction.article_id == article_id)
        result = await session.execute(query)
        avg_price = result.scalar()
        
        # Si no hay transacciones, usar un precio base
        if avg_price is None:
            return 29.99 + (article_id % 100)  # Precio mock variado
        
        return float(avg_price)
    except:
        return 29.99 + (article_id % 100)  # Fallback