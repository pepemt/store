"""
Rutas de la API para el manejo de productos (normalizadas para el front).
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from database.lib import Database
from database.models import Article, Transaction
from ..s3_service import S3Service

router = APIRouter()


# --------- MODELOS DE RESPUESTA (shape que espera el front) ---------

class ProductResponse(BaseModel):
    """
    Modelo de producto normalizado para el front.
    - id <= article_id
    - name <= prod_name
    - description <= detail_desc
    - category <= product_group_name (categoría comercial)
    - department <= department_name
    - price calculado de transacciones (fallback estable)
    - images: intenta S3 (products/{article_id}.jpg), fallback a picsum
    """
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    price: float = 0.0
    stock: int = 100
    rating: float = 4.0
    images: List[str] = []
    # Extras útiles
    color_group: Optional[str] = None
    product_type: Optional[str] = None
    product_group: Optional[str] = None


class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class CategoryResponse(BaseModel):
    categories: List[str]


class FilterOptionsResponse(BaseModel):
    """Opciones disponibles para filtros."""
    categories: List[str]
    colors: List[str]
    product_types: List[str]
    departments: List[str]
    price_range: dict  # {"min": float, "max": float}


class ProductIdResponse(BaseModel):
    id: int
    name: str


class ProductIdListResponse(BaseModel):
    products: List[ProductIdResponse]
    total: int
    limit: int


# --------- HELPERS ---------

def _fallback_image(article_id: int) -> str | None:
    # No hay fallback - el frontend mostrará un placeholder
    return None


def _candidate_image_keys(article_id: int) -> List[str]:
    # Las imágenes en S3 tienen IDs con padding de 10 dígitos (ej: 0108775015.jpg)
    padded_id = str(article_id).zfill(10)
    return [
        f"products/{padded_id}.jpg",
        f"products/{padded_id}.png",
        f"products/{padded_id}.webp",
    ]


def _build_images(article_id: int) -> List[str]:
    """
    Genera URLs de imágenes usando el proxy del backend.
    El proxy sirve imágenes desde S3 a través de /api/v1/images/{key}
    """
    try:
        # Obtener la URL base del backend desde variables de entorno
        import os
        backend_url = (os.getenv("FASTAPI_PUBLIC_URL") or "").rstrip("/")

        # Verificar si la imagen existe en S3
        for key in _candidate_image_keys(article_id):
            if S3Service.image_exists(key):
                # Usar proxy del backend en lugar de URLs presignadas
                # Esto evita problemas de permisos y expiración
                return [f"{backend_url}/api/v1/images/{key}"]
    except Exception:
        pass
    return [_fallback_image(article_id)]


async def _get_average_price(session, article_id: int) -> float:
    """
    Precio promedio por article_id; si no hay transacciones, fallback estable.
    Todos los precios se multiplican por 590.
    """
    PRICE_MULTIPLIER = 1.0
    try:
        q = select(func.avg(Transaction.price)).where(Transaction.article_id == article_id)
        result = await session.execute(q)
        avg_price = result.scalar()
        if avg_price is None:
            # Fallback "determinístico" para que no cambie en cada request
            base = 29.99
            return float((base + (article_id % 100)) * PRICE_MULTIPLIER)
        return float(avg_price * PRICE_MULTIPLIER)
    except Exception:
        base = 29.99
        return float((base + (article_id % 100)) * PRICE_MULTIPLIER)


def _to_product_response(row: Article, price: float) -> ProductResponse:
    """
    Mapea Article → ProductResponse con el shape esperado por el front.
    """
    return ProductResponse(
        id=row.article_id,
        name=row.prod_name,
        description=row.detail_desc,
        category=row.product_group_name,     # categoría comercial
        department=row.department_name,
        price=price,
        stock=100,                           # mock hasta tener inventario real
        rating=4.0 + (row.article_id % 10) / 10,
        images=_build_images(row.article_id),
        color_group=row.colour_group_name,
        product_type=row.product_type_name,
        product_group=row.product_group_name,
    )


# --------- ENDPOINTS ---------

@router.get("/", response_model=ProductListResponse)
async def get_products(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Productos por página"),
    search: Optional[str] = Query(None, description="Término de búsqueda"),
    category: Optional[str] = Query(None, description="Filtrar por categoría (product_group_name)"),
    department: Optional[str] = Query(None, description="Filtrar por departamento"),
    color_group: Optional[str] = Query(None, description="Filtrar por color"),
    product_type: Optional[str] = Query(None, description="Filtrar por tipo de producto"),
    price_min: Optional[float] = Query(None, ge=0, description="Precio mínimo"),
    price_max: Optional[float] = Query(None, ge=0, description="Precio máximo"),
):
    """
    Lista de productos con paginación y filtros.
    Filtros:
      - search: ILIKE en nombre, descripción, tipo y grupo
      - category: product_group_name
      - department: department_name
      - color_group: colour_group_name
      - product_type: product_type_name
      - price_min/price_max: rango de precios
    """
    try:
        async with Database.get_session() as session:
            # Base
            base_q = select(Article)
            count_q = select(func.count(Article.article_id))

            # Filtros
            conditions = []

            if search:
                # Usamos ILIKE nativo de Postgres
                like = f"%{search}%"
                conditions.append(or_(
                    Article.prod_name.ilike(like),
                    Article.detail_desc.ilike(like),
                    Article.product_type_name.ilike(like),
                    Article.product_group_name.ilike(like),
                ))

            if category:
                conditions.append(Article.product_group_name == category)

            if department:
                conditions.append(Article.department_name == department)

            if color_group:
                conditions.append(Article.colour_group_name == color_group)

            if product_type:
                conditions.append(Article.product_type_name == product_type)

            if conditions:
                base_q = base_q.where(*conditions)
                count_q = count_q.where(*conditions)

            # Filtro de precio (requiere subquery para avg de transacciones)
            # Para simplificar, aplicamos el filtro después de obtener resultados
            # si hay filtro de precio activo
            has_price_filter = price_min is not None or price_max is not None

            # Total
            total = (await session.execute(count_q)).scalar() or 0

            # Paginación
            offset = (page - 1) * per_page
            q = base_q.order_by(Article.article_id).offset(offset).limit(per_page)

            # Si hay filtro de precio, necesitamos obtener más resultados y filtrar
            if has_price_filter:
                # Obtener más productos para compensar los que serán filtrados
                q = base_q.order_by(Article.article_id).limit(per_page * 5)
                rows = (await session.execute(q)).scalars().all()

                # Mapear y filtrar por precio
                products: List[ProductResponse] = []
                for row in rows:
                    price = await _get_average_price(session, row.article_id)
                    if price_min is not None and price < price_min:
                        continue
                    if price_max is not None and price > price_max:
                        continue
                    products.append(_to_product_response(row, price))
                    if len(products) >= per_page:
                        break

                # Para filtros de precio, el total es aproximado
                filtered_total = len(products)
                total_pages = 1  # Simplificado para filtros de precio
            else:
                rows = (await session.execute(q)).scalars().all()

                # Mapear a respuesta
                products = []
                for row in rows:
                    price = await _get_average_price(session, row.article_id)
                    products.append(_to_product_response(row, price))

                total_pages = (total + per_page - 1) // per_page

            return ProductListResponse(
                products=products,
                total=total if not has_price_filter else len(products),
                page=page,
                per_page=per_page,
                total_pages=total_pages,
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener productos: {str(e)}",
        )


@router.get("/search", response_model=ProductListResponse)
async def search_products(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    limit: int = Query(20, ge=1, le=100, description="Límite de resultados"),
):
    """
    Búsqueda rápida (devuelve estructura de lista para que el front no haga casos especiales).
    """
    try:
        async with Database.get_session() as session:
            like = f"%{q}%"
            qsel = (
                select(Article)
                .where(or_(
                    Article.prod_name.ilike(like),
                    Article.detail_desc.ilike(like),
                    Article.product_type_name.ilike(like),
                    Article.product_group_name.ilike(like),
                ))
                .order_by(Article.article_id)
                .limit(limit)
            )

            rows = (await session.execute(qsel)).scalars().all()

            products: List[ProductResponse] = []
            for row in rows:
                price = await _get_average_price(session, row.article_id)
                products.append(_to_product_response(row, price))

            return ProductListResponse(
                products=products,
                total=len(products),
                page=1,
                per_page=limit,
                total_pages=1,
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en búsqueda: {str(e)}",
        )


@router.get("/categories", response_model=CategoryResponse)
async def get_categories():
    """
    Devuelve categorías comerciales (product_group_name).
    """
    try:
        async with Database.get_session() as session:
            q = select(Article.product_group_name).distinct().order_by(Article.product_group_name)
            result = await session.execute(q)
            categories = [row[0] for row in result.fetchall() if row[0]]
            return CategoryResponse(categories=categories)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener categorías: {str(e)}",
        )


@router.get("/departments", response_model=CategoryResponse)
async def get_departments():
    """
    Devuelve departamentos (department_name).
    """
    try:
        async with Database.get_session() as session:
            q = select(Article.department_name).distinct().order_by(Article.department_name)
            result = await session.execute(q)
            departments = [row[0] for row in result.fetchall() if row[0]]
            return CategoryResponse(categories=departments)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener departamentos: {str(e)}",
        )


@router.get("/filters", response_model=FilterOptionsResponse)
async def get_filter_options():
    """
    Devuelve todas las opciones disponibles para filtros.
    Consolidado en un solo endpoint para reducir requests del frontend.
    """
    try:
        async with Database.get_session() as session:
            # Categorías
            q_cat = select(Article.product_group_name).distinct().order_by(Article.product_group_name)
            categories = [r[0] for r in (await session.execute(q_cat)).fetchall() if r[0]]

            # Colores
            q_colors = select(Article.colour_group_name).distinct().order_by(Article.colour_group_name)
            colors = [r[0] for r in (await session.execute(q_colors)).fetchall() if r[0]]

            # Tipos de producto
            q_types = select(Article.product_type_name).distinct().order_by(Article.product_type_name)
            product_types = [r[0] for r in (await session.execute(q_types)).fetchall() if r[0]]

            # Departamentos
            q_dept = select(Article.department_name).distinct().order_by(Article.department_name)
            departments = [r[0] for r in (await session.execute(q_dept)).fetchall() if r[0]]

            # Rango de precios (de transacciones)
            q_price = select(
                func.min(Transaction.price),
                func.max(Transaction.price)
            )
            price_result = (await session.execute(q_price)).fetchone()
            price_range = {
                "min": float(price_result[0]) if price_result[0] else 0.0,
                "max": float(price_result[1]) if price_result[1] else 1000.0,
            }

            return FilterOptionsResponse(
                categories=categories,
                colors=colors,
                product_types=product_types,
                departments=departments,
                price_range=price_range,
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener opciones de filtros: {str(e)}",
        )


@router.get("/ids", response_model=ProductIdListResponse)
async def get_product_ids(
    limit: int = Query(100, ge=1, le=10000, description="Límite de productos"),
    offset: int = Query(0, ge=0, description="Offset"),
):
    """
    Lista ligera de {id, name} para utilidades de front/autocomplete.
    """
    try:
        async with Database.get_session() as session:
            q = (
                select(Article.article_id, Article.prod_name)
                .order_by(Article.article_id)
                .offset(offset)
                .limit(limit)
            )
            rows = (await session.execute(q)).fetchall()

            count_q = select(func.count(Article.article_id))
            total = (await session.execute(count_q)).scalar() or 0

            products = [ProductIdResponse(id=r[0], name=r[1]) for r in rows]
            return ProductIdListResponse(products=products, total=total, limit=limit)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener IDs de productos: {str(e)}",
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product_by_id(product_id: int):
    """
    Detalle por ID (usa article_id como clave pública).
    """
    try:
        async with Database.get_session() as session:
            q = select(Article).where(Article.article_id == product_id)
            row = (await session.execute(q)).scalar_one_or_none()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Producto no encontrado",
                )

            price = await _get_average_price(session, row.article_id)
            return _to_product_response(row, price)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener producto: {str(e)}",
        )
