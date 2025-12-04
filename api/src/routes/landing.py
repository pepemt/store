"""
Rutas de la API para la landing page (categorías con imágenes, bestsellers, etc.).
"""

import os
import re
import time
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func, desc
from database.lib import Database
from database.models import Article, Transaction, Review

router = APIRouter()


# --------- SISTEMA DE CACHÉ EN MEMORIA ---------

class MemoryCache:
    """Caché simple en memoria con TTL."""
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def get(self, key: str, ttl_seconds: int = 600) -> Optional[Any]:
        """Obtiene valor del caché si existe y no ha expirado."""
        if key not in self._cache:
            return None
        if time.time() - self._timestamps.get(key, 0) > ttl_seconds:
            # Expirado
            del self._cache[key]
            del self._timestamps[key]
            return None
        return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """Guarda valor en caché."""
        self._cache[key] = value
        self._timestamps[key] = time.time()

    def get_lock(self, key: str) -> asyncio.Lock:
        """Obtiene lock para evitar múltiples cálculos simultáneos."""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]


# Instancia global del caché
_cache = MemoryCache()

# TTL en segundos (10 minutos para bestsellers)
BESTSELLERS_TTL = 600
REVIEWS_TTL = 600


async def warmup_cache():
    """
    Pre-calienta el caché de bestsellers y reviews.
    Llamar esto en el startup del servidor.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info("Precalentando caché de landing...")

        # Pre-calentar bestsellers (el más costoso)
        products = await _fetch_bestsellers_from_db(8)
        _cache.set("bestsellers_8", products)
        logger.info(f"  Bestsellers cacheados: {len(products)} productos")

        # Pre-calentar featured reviews (usa la misma query costosa)
        reviews = await _fetch_featured_reviews_from_db(6)
        _cache.set("featured_reviews_6", reviews)
        logger.info(f"  Reviews cacheados: {len(reviews)} reviews")

        logger.info("Caché de landing precalentado correctamente")
    except Exception as e:
        logger.warning(f"Error al precalentar caché de landing (no crítico): {e}")


# --------- MODELOS DE RESPUESTA ---------

class CategoryWithImage(BaseModel):
    """Categoría con imagen representativa."""
    name: str
    slug: str
    image_url: str
    product_count: int
    representative_product_id: int


class CategoriesWithImagesResponse(BaseModel):
    categories: List[CategoryWithImage]


class DepartmentWithImage(BaseModel):
    """Departamento con imagen representativa."""
    name: str
    slug: str
    image_url: str
    product_count: int


class DepartmentsWithImagesResponse(BaseModel):
    departments: List[DepartmentWithImage]


class ProductResponse(BaseModel):
    """Modelo de producto para las secciones de landing."""
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    price: float = 0.0
    stock: int = 100
    rating: float = 4.0
    images: List[str] = []
    color_group: Optional[str] = None
    product_type: Optional[str] = None
    sales_count: Optional[int] = None


class BestsellersResponse(BaseModel):
    products: List[ProductResponse]
    period: str = "all_time"


class NewArrivalsResponse(BaseModel):
    products: List[ProductResponse]


class FeaturedReview(BaseModel):
    """Review destacado para testimonios."""
    product_id: int
    product_name: str
    product_image: str
    reviewer_name: str
    review_text: str
    rating: float


class FeaturedReviewsResponse(BaseModel):
    reviews: List[FeaturedReview]


class NewsletterSubscribeRequest(BaseModel):
    email: EmailStr


class NewsletterSubscribeResponse(BaseModel):
    success: bool
    message: str


# --------- HELPERS ---------

def _slugify(text: str) -> str:
    """Convierte texto a slug URL-friendly."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text


def _build_image_url(article_id: int) -> str:
    """
    Construye la URL de imagen usando el proxy del backend.
    NO verifica existencia en S3 para evitar latencia.
    """
    backend_url = os.getenv("FASTAPI_PUBLIC_URL", "")
    padded_id = str(article_id).zfill(10)
    return f"{backend_url}/api/v1/images/products/{padded_id}.jpg"


def _deterministic_price(article_id: int) -> float:
    """Genera un precio determinístico basado en el article_id."""
    base = 29.99
    return float(base + (article_id % 100))


async def _get_prices_batch(session, article_ids: List[int]) -> Dict[int, float]:
    """
    Obtiene precios promedio para múltiples artículos en UNA sola query.
    Elimina el problema N+1.
    """
    if not article_ids:
        return {}

    try:
        q = (
            select(
                Transaction.article_id,
                func.avg(Transaction.price).label('avg_price')
            )
            .where(Transaction.article_id.in_(article_ids))
            .group_by(Transaction.article_id)
        )
        result = await session.execute(q)
        return {row.article_id: float(row.avg_price) for row in result.fetchall()}
    except Exception:
        return {}


def _article_to_product(row: Article, price: float, sales_count: Optional[int] = None) -> ProductResponse:
    """Convierte Article a ProductResponse."""
    return ProductResponse(
        id=row.article_id,
        name=row.prod_name,
        description=row.detail_desc,
        category=row.product_group_name,
        department=row.department_name,
        price=price,
        stock=100,
        rating=4.0 + (row.article_id % 10) / 10,
        images=[_build_image_url(row.article_id)],
        color_group=row.colour_group_name,
        product_type=row.product_type_name,
        sales_count=sales_count,
    )


# --------- ENDPOINTS OPTIMIZADOS ---------

@router.get("/categories-with-images", response_model=CategoriesWithImagesResponse)
async def get_categories_with_images(
    limit: int = Query(8, ge=1, le=20, description="Número máximo de categorías"),
):
    """
    Obtiene las categorías con una imagen representativa.
    OPTIMIZADO: Una sola query simple sin JOIN a Transaction.
    """
    try:
        async with Database.get_session() as session:
            # Query simple: categorías con producto representativo y conteo
            # Sin JOIN a Transaction = MUCHO más rápido
            q = (
                select(
                    Article.product_group_name,
                    func.min(Article.article_id).label('rep_article_id'),
                    func.count(Article.article_id).label('product_count')
                )
                .where(Article.product_group_name != None)
                .group_by(Article.product_group_name)
                .order_by(desc(func.count(Article.article_id)))
                .limit(limit)
            )

            result = await session.execute(q)
            rows = result.fetchall()

            categories = []
            for row in rows:
                cat_name = row.product_group_name
                article_id = row.rep_article_id
                count = row.product_count

                if cat_name:
                    categories.append(CategoryWithImage(
                        name=cat_name,
                        slug=_slugify(cat_name),
                        image_url=_build_image_url(article_id),
                        product_count=count,
                        representative_product_id=article_id,
                    ))

            return CategoriesWithImagesResponse(categories=categories)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener categorías: {str(e)}",
        )


@router.get("/departments-with-images", response_model=DepartmentsWithImagesResponse)
async def get_departments_with_images(
    limit: int = Query(6, ge=1, le=10, description="Número máximo de departamentos"),
):
    """
    Obtiene los departamentos con una imagen representativa.
    OPTIMIZADO: Una sola query simple sin JOIN a Transaction.
    """
    try:
        async with Database.get_session() as session:
            # Query simple sin JOIN a Transaction
            q = (
                select(
                    Article.department_name,
                    func.min(Article.article_id).label('rep_article_id'),
                    func.count(Article.article_id).label('product_count')
                )
                .where(Article.department_name != None)
                .group_by(Article.department_name)
                .order_by(desc(func.count(Article.article_id)))
                .limit(limit)
            )

            result = await session.execute(q)
            rows = result.fetchall()

            departments = []
            for row in rows:
                dept_name = row.department_name
                article_id = row.rep_article_id
                count = row.product_count

                if dept_name:
                    departments.append(DepartmentWithImage(
                        name=dept_name,
                        slug=_slugify(dept_name),
                        image_url=_build_image_url(article_id),
                        product_count=count,
                    ))

            return DepartmentsWithImagesResponse(departments=departments)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener departamentos: {str(e)}",
        )


async def _fetch_bestsellers_from_db(limit: int) -> List[ProductResponse]:
    """
    Obtiene los bestsellers de la BD (query costosa).
    Solo se llama cuando el caché está vacío o expirado.
    """
    async with Database.get_session() as session:
        # Query principal: productos más vendidos
        sales_count_col = func.count(Transaction.id).label('sales_count')
        q = (
            select(Article, sales_count_col)
            .join(Transaction, Transaction.article_id == Article.article_id)
            .group_by(Article.article_id)
            .order_by(desc(sales_count_col))
            .limit(limit)
        )

        result = await session.execute(q)
        rows = result.fetchall()

        # Obtener IDs de artículos
        article_ids = [row[0].article_id for row in rows]

        # BATCH: Una sola query para todos los precios
        prices = await _get_prices_batch(session, article_ids)

        # Mapear a respuesta
        products = []
        for row in rows:
            article = row[0]
            sales = row[1]
            price = prices.get(article.article_id, _deterministic_price(article.article_id))
            products.append(_article_to_product(article, price, sales))

        return products


@router.get("/bestsellers", response_model=BestsellersResponse)
async def get_bestsellers(
    limit: int = Query(8, ge=1, le=20, description="Número de productos"),
):
    """
    Obtiene los productos más vendidos.
    OPTIMIZADO: Caché en memoria por 10 minutos.
    """
    cache_key = f"bestsellers_{limit}"

    # 1. Intentar obtener del caché
    cached = _cache.get(cache_key, BESTSELLERS_TTL)
    if cached is not None:
        return BestsellersResponse(products=cached, period="all_time")

    # 2. Si no está en caché, calcular (con lock para evitar thundering herd)
    try:
        lock = _cache.get_lock(cache_key)
        async with lock:
            # Double-check después del lock
            cached = _cache.get(cache_key, BESTSELLERS_TTL)
            if cached is not None:
                return BestsellersResponse(products=cached, period="all_time")

            # Fetch de la BD
            products = await _fetch_bestsellers_from_db(limit)

            # Guardar en caché
            _cache.set(cache_key, products)

            return BestsellersResponse(products=products, period="all_time")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener bestsellers: {str(e)}",
        )


@router.get("/new-arrivals", response_model=NewArrivalsResponse)
async def get_new_arrivals(
    limit: int = Query(8, ge=1, le=20, description="Número de productos"),
):
    """
    Obtiene los productos más recientes.
    OPTIMIZADO: Usa batch para precios en lugar de N+1 queries.
    """
    try:
        async with Database.get_session() as session:
            # Query principal: productos más recientes
            q = (
                select(Article)
                .order_by(desc(Article.article_id))
                .limit(limit)
            )

            result = await session.execute(q)
            articles = result.scalars().all()

            # BATCH: Una sola query para todos los precios
            article_ids = [a.article_id for a in articles]
            prices = await _get_prices_batch(session, article_ids)

            # Mapear a respuesta
            products = []
            for article in articles:
                price = prices.get(article.article_id, _deterministic_price(article.article_id))
                products.append(_article_to_product(article, price))

            return NewArrivalsResponse(products=products)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener nuevos productos: {str(e)}",
        )


async def _fetch_featured_reviews_from_db(limit: int) -> List[FeaturedReview]:
    """
    Obtiene reviews destacados de la BD.
    Usa reviews reales con alta puntuación (4-5 estrellas).
    Solo se llama cuando el caché está vacío o expirado.
    """
    # Nombres para generar reviewers anónimos de manera consistente
    reviewer_names = [
        "María G.", "Carlos L.", "Ana M.", "Pedro S.", "Laura R.",
        "Juan H.", "Sofia D.", "Miguel T.", "Elena R.", "David M.",
        "Carmen J.", "Pablo A.", "Isabel F.", "Antonio V.", "Rosa P.",
    ]

    async with Database.get_session() as session:
        # Primero intentar obtener reviews reales de la tabla Review
        try:
            review_query = (
                select(Review, Article)
                .join(Article, Review.article_id == Article.article_id)
                .where(Review.review_stars >= 4)
                .order_by(desc(Review.review_stars), func.random())
                .limit(limit)
            )
            result = await session.execute(review_query)
            rows = result.all()

            if rows:
                reviews = []
                for i, (review, article) in enumerate(rows):
                    reviews.append(FeaturedReview(
                        product_id=article.article_id,
                        product_name=article.prod_name,
                        product_image=_build_image_url(article.article_id),
                        reviewer_name=reviewer_names[review.id % len(reviewer_names)],
                        review_text=review.review_text,
                        rating=float(review.review_stars),
                    ))
                return reviews
        except Exception:
            # Si falla (tabla no existe aún), usar fallback
            pass

        # Fallback: generar reviews basados en productos populares
        sales_count_col = func.count(Transaction.id).label('sales_count')
        q = (
            select(Article, sales_count_col)
            .join(Transaction, Transaction.article_id == Article.article_id)
            .group_by(Article.article_id)
            .order_by(desc(sales_count_col))
            .limit(limit)
        )

        result = await session.execute(q)
        rows = result.fetchall()

        review_templates = [
            "Excelente calidad, superó mis expectativas. El {product} es exactamente lo que buscaba.",
            "Me encantó el {product}. La tela es muy suave y el corte perfecto.",
            "Muy satisfecha con mi compra. El {product} llegó rápido y bien empacado.",
            "Gran relación calidad-precio. El {product} se ve tal como en las fotos.",
            "Increíble {product}! Ya es mi favorito, muy cómodo y elegante.",
            "Recomiendo totalmente. El {product} tiene acabados de primera.",
        ]

        reviews = []
        for i, row in enumerate(rows):
            article = row[0]
            product_type = article.product_type_name.lower() if article.product_type_name else "producto"

            reviews.append(FeaturedReview(
                product_id=article.article_id,
                product_name=article.prod_name,
                product_image=_build_image_url(article.article_id),
                reviewer_name=reviewer_names[i % len(reviewer_names)],
                review_text=review_templates[i % len(review_templates)].format(product=product_type),
                rating=4.5 + (i % 3) * 0.2,
            ))

        return reviews


@router.get("/featured-reviews", response_model=FeaturedReviewsResponse)
async def get_featured_reviews(
    limit: int = Query(6, ge=1, le=12, description="Número de reviews"),
):
    """
    Obtiene reviews destacados para testimonios.
    OPTIMIZADO: Caché en memoria por 10 minutos.
    """
    cache_key = f"featured_reviews_{limit}"

    # 1. Intentar obtener del caché
    cached = _cache.get(cache_key, REVIEWS_TTL)
    if cached is not None:
        return FeaturedReviewsResponse(reviews=cached)

    # 2. Si no está en caché, calcular
    try:
        lock = _cache.get_lock(cache_key)
        async with lock:
            # Double-check después del lock
            cached = _cache.get(cache_key, REVIEWS_TTL)
            if cached is not None:
                return FeaturedReviewsResponse(reviews=cached)

            # Fetch de la BD
            reviews = await _fetch_featured_reviews_from_db(limit)

            # Guardar en caché
            _cache.set(cache_key, reviews)

            return FeaturedReviewsResponse(reviews=reviews)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reviews: {str(e)}",
        )


@router.post("/newsletter/subscribe", response_model=NewsletterSubscribeResponse)
async def subscribe_newsletter(request: NewsletterSubscribeRequest):
    """Suscribe un email al newsletter."""
    try:
        return NewsletterSubscribeResponse(
            success=True,
            message=f"¡Gracias por suscribirte! Recibirás nuestras ofertas en {request.email}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al suscribir: {str(e)}",
        )


@router.get("/promo-banner")
async def get_promo_banner():
    """Retorna el contenido del banner promocional."""
    return {
        "title": "Envío Gratis",
        "subtitle": "En compras mayores a $500",
        "description": "Disfruta de envío gratuito en tu próxima compra. Aplica en todo el catálogo.",
        "cta_text": "Comprar Ahora",
        "cta_link": "/products",
        "background_color": "#6e348d",
        "accent_color": "#ffb320",
    }
