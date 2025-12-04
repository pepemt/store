"""
Rutas de la API para el manejo de reviews de productos.
"""

import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from database.lib import Database
from database.models import Review, Article

router = APIRouter()


# --------- MODELOS DE RESPUESTA ---------

class ReviewResponse(BaseModel):
    """Review individual."""
    id: int
    article_id: int
    review_text: str
    review_stars: int
    customer_id: Optional[str] = None
    date: Optional[str] = None
    cluster_label: Optional[str] = None


class ProductReviewsResponse(BaseModel):
    """Reviews de un producto con estadísticas."""
    reviews: List[ReviewResponse]
    total: int
    average_rating: float
    page: int
    per_page: int


class FeaturedReviewResponse(BaseModel):
    """Review destacado para landing/testimonios."""
    product_id: int
    product_name: str
    product_image: str
    reviewer_name: str
    review_text: str
    rating: float


class FeaturedReviewsListResponse(BaseModel):
    """Lista de reviews destacados."""
    reviews: List[FeaturedReviewResponse]


# --------- HELPERS ---------

def _build_image_url(article_id: int) -> str:
    """Construye URL de imagen usando el proxy del backend."""
    backend_url = (os.getenv("FASTAPI_PUBLIC_URL") or "").rstrip("/")
    padded_id = str(article_id).zfill(10)
    return f"{backend_url}/api/v1/images/products/{padded_id}.jpg"


def _generate_reviewer_name(customer_id: Optional[str], review_id: int) -> str:
    """Genera un nombre de reviewer anónimo pero consistente."""
    names = [
        "María G.", "Carlos L.", "Ana M.", "Pedro S.", "Laura R.",
        "Juan H.", "Sofia D.", "Miguel T.", "Elena R.", "David M.",
        "Carmen J.", "Pablo A.", "Isabel F.", "Antonio V.", "Rosa P.",
    ]
    # Usar el review_id para seleccionar un nombre consistente
    return names[review_id % len(names)]


# --------- ENDPOINTS ---------

@router.get("/product/{article_id}", response_model=ProductReviewsResponse)
async def get_product_reviews(
    article_id: int,
    limit: int = Query(10, ge=1, le=50, description="Número de reviews por página"),
    page: int = Query(1, ge=1, description="Número de página"),
):
    """
    Obtiene reviews de un producto específico.
    """
    try:
        offset = (page - 1) * limit

        async with Database.get_session() as session:
            # Obtener reviews
            reviews_query = (
                select(Review)
                .where(Review.article_id == article_id)
                .order_by(desc(Review.review_stars))
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(reviews_query)
            reviews = result.scalars().all()

            # Obtener estadísticas
            stats_query = select(
                func.count(Review.id).label('total'),
                func.avg(Review.review_stars).label('average')
            ).where(Review.article_id == article_id)
            stats_result = await session.execute(stats_query)
            stats = stats_result.first()

            total = stats.total or 0
            average = float(stats.average) if stats.average else 0.0

            return ProductReviewsResponse(
                reviews=[
                    ReviewResponse(
                        id=r.id,
                        article_id=r.article_id,
                        review_text=r.review_text,
                        review_stars=r.review_stars,
                        customer_id=r.customer_id,
                        date=str(r.t_dat) if r.t_dat else None,
                        cluster_label=r.cluster_label,
                    )
                    for r in reviews
                ],
                total=total,
                average_rating=round(average, 1),
                page=page,
                per_page=limit,
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reviews: {str(e)}",
        )


@router.get("/featured", response_model=FeaturedReviewsListResponse)
async def get_featured_reviews(
    limit: int = Query(6, ge=1, le=12, description="Número de reviews destacados"),
):
    """
    Obtiene reviews destacados para la landing page.
    Selecciona reviews con 4-5 estrellas de productos populares.
    """
    try:
        async with Database.get_session() as session:
            # Obtener reviews con alta puntuación y unir con artículos
            query = (
                select(Review, Article)
                .join(Article, Review.article_id == Article.article_id)
                .where(Review.review_stars >= 4)
                .order_by(desc(Review.review_stars), func.random())
                .limit(limit)
            )
            result = await session.execute(query)
            rows = result.all()

            reviews = []
            for review, article in rows:
                reviews.append(FeaturedReviewResponse(
                    product_id=article.article_id,
                    product_name=article.prod_name,
                    product_image=_build_image_url(article.article_id),
                    reviewer_name=_generate_reviewer_name(review.customer_id, review.id),
                    review_text=review.review_text,
                    rating=float(review.review_stars),
                ))

            return FeaturedReviewsListResponse(reviews=reviews)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reviews destacados: {str(e)}",
        )


@router.get("/stats/{article_id}")
async def get_review_stats(article_id: int):
    """
    Obtiene estadísticas de reviews para un producto.
    """
    try:
        stats = await Database.get_review_stats_by_article(article_id)
        return {
            "article_id": article_id,
            "total_reviews": stats['total'],
            "average_rating": round(stats['average'], 1),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}",
        )
