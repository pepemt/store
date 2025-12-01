from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.lib import Database
from database.models import Order, OrderStatus

from ..model_loader import get_model

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/products",
    tags=["recommendations"],
)


# =========================
#  ESQUEMAS Pydantic
# =========================

class UserRecommendRequest(BaseModel):
    user_id: str
    N: int = 10


class SimilarItemsRequest(BaseModel):
    article_id: str
    N: int = 10


class UserRecommendation(BaseModel):
    user_id: str
    article_id: str
    score: float


class ProductSimilarity(BaseModel):
    article_id: str
    score: float


# =========================
#  HELPERS
# =========================

def _get_similar_items_internal(article_id: str, n: int = 5) -> List[ProductSimilarity]:
    """
    Obtiene productos similares a un artículo usando el modelo ALS.
    Versión interna que no lanza excepciones HTTP, retorna lista vacía en caso de error.
    """
    try:
        model = get_model()

        py_model = getattr(getattr(model, "_model_impl", None), "python_model", None)
        if py_model is None:
            return []

        item_map = getattr(py_model, "item_map", None)
        rev_item_map = getattr(py_model, "rev_item_map", None)
        als_model = getattr(py_model, "model", None)

        if item_map is None or rev_item_map is None or als_model is None:
            return []

        article_id_str = str(article_id)
        idx = item_map.get(article_id_str)
        if idx is None:
            return []

        recs = als_model.similar_items(idx, N=n + 1)

        if isinstance(recs, tuple):
            item_indices, scores = recs
        else:
            item_indices = [item for item, _ in recs]
            scores = [score for _, score in recs]

        results: List[ProductSimilarity] = []
        for i, s in zip(item_indices, scores):
            aid = rev_item_map.get(int(i))
            if aid is None or aid == article_id_str:
                continue

            results.append(
                ProductSimilarity(
                    article_id=str(aid),
                    score=float(s),
                )
            )

            if len(results) >= n:
                break

        return results
    except Exception as e:
        logger.warning(f"Error obteniendo similares para {article_id}: {e}")
        return []


async def _get_user_purchased_articles(customer_id: str, limit: int = 3) -> List[int]:
    """
    Obtiene los article_id de los productos comprados por el usuario.
    Retorna los 'limit' productos más recientes de órdenes pagadas.
    """
    try:
        async with Database.get_session() as session:
            # Obtener órdenes pagadas del usuario, ordenadas por fecha desc
            query = (
                select(Order)
                .options(selectinload(Order.items))
                .where(
                    Order.customer_id == customer_id,
                    Order.status == OrderStatus.PAID.value
                )
                .order_by(Order.paid_at.desc())
                .limit(10)  # Limitar a las 10 órdenes más recientes
            )

            result = await session.execute(query)
            orders = result.scalars().all()

            # Extraer article_ids únicos, manteniendo el orden (más recientes primero)
            seen = set()
            article_ids = []

            for order in orders:
                for item in order.items:
                    if item.article_id not in seen:
                        seen.add(item.article_id)
                        article_ids.append(item.article_id)
                        if len(article_ids) >= limit:
                            return article_ids

            return article_ids
    except Exception as e:
        logger.error(f"Error obteniendo compras del usuario {customer_id}: {e}")
        return []


# =========================
#  ENDPOINTS
# =========================

@router.post("/recommend/user", response_model=List[UserRecommendation])
async def recommend_for_user(payload: UserRecommendRequest) -> List[UserRecommendation]:
    """
    Devuelve recomendaciones de productos para un usuario basadas en sus compras anteriores.

    Estrategia:
    1. Obtiene los 3 productos más recientes que el usuario compró
    2. Para cada producto, obtiene productos similares usando el modelo ALS
    3. Combina y deduplica los resultados, ordenados por score

    Si el usuario no tiene compras, retorna lista vacía.
    """
    customer_id = payload.user_id
    n_recommendations = payload.N

    # 1. Obtener los productos comprados por el usuario
    purchased_articles = await _get_user_purchased_articles(customer_id, limit=3)

    if not purchased_articles:
        logger.info(f"Usuario {customer_id} no tiene compras, sin recomendaciones")
        return []

    logger.info(f"Usuario {customer_id} tiene {len(purchased_articles)} productos comprados: {purchased_articles}")

    # 2. Para cada producto comprado, obtener similares
    all_similar: dict[str, float] = {}  # article_id -> max_score
    purchased_set = set(str(a) for a in purchased_articles)

    for article_id in purchased_articles:
        similar_items = _get_similar_items_internal(str(article_id), n=n_recommendations)

        for item in similar_items:
            # Excluir productos que el usuario ya compró
            if item.article_id in purchased_set:
                continue

            # Mantener el score más alto si el producto aparece múltiples veces
            if item.article_id not in all_similar or item.score > all_similar[item.article_id]:
                all_similar[item.article_id] = item.score

    if not all_similar:
        logger.info(f"No se encontraron productos similares para las compras del usuario {customer_id}")
        return []

    # 3. Ordenar por score y tomar los top N
    sorted_recommendations = sorted(
        all_similar.items(),
        key=lambda x: x[1],
        reverse=True
    )[:n_recommendations]

    # 4. Construir respuesta
    results: List[UserRecommendation] = []
    for article_id, score in sorted_recommendations:
        results.append(
            UserRecommendation(
                user_id=customer_id,
                article_id=article_id,
                score=score,
            )
        )

    logger.info(f"Generadas {len(results)} recomendaciones para usuario {customer_id}")
    return results


@router.post("/similar", response_model=List[ProductSimilarity])
def similar_items(payload: SimilarItemsRequest) -> List[ProductSimilarity]:
    """
    Devuelve artículos similares a un artículo dado usando el modelo ALS en modo item-based.

    Aprovecha el ALS ya entrenado (mismo modelo que las recomendaciones por usuario)
    accediendo al modelo interno de Python (ALSWrapper) cargado mediante MLflow.
    """
    model = get_model()

    # Acceso al PythonModel interno (ALSWrapper) registrado en MLflow.
    py_model = getattr(getattr(model, "_model_impl", None), "python_model", None)
    if py_model is None:
        raise HTTPException(
            status_code=500,
            detail="No se pudo acceder al modelo interno ALSWrapper desde MLflow.",
        )

    item_map = getattr(py_model, "item_map", None)
    rev_item_map = getattr(py_model, "rev_item_map", None)
    als_model = getattr(py_model, "model", None)

    if item_map is None or rev_item_map is None or als_model is None:
        raise HTTPException(
            status_code=500,
            detail="El modelo interno no expone los mapas de artículos o el modelo ALS.",
        )

    article_id_str = str(payload.article_id)
    idx = item_map.get(article_id_str)
    if idx is None:
        # Si el artículo no existe en el modelo, retornar vacío
        return []

    try:
        recs = als_model.similar_items(idx, N=payload.N + 1)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error al calcular artículos similares: {exc}",
        )

    # `similar_items` puede regresar lista de tuplas (idx, score) o (indices, scores)
    if isinstance(recs, tuple):
        item_indices, scores = recs
    else:
        item_indices = [item for item, _ in recs]
        scores = [score for _, score in recs]

    results: List[ProductSimilarity] = []
    for i, s in zip(item_indices, scores):
        aid = rev_item_map.get(int(i))
        # Excluir el mismo artículo de entrada
        if aid is None or aid == article_id_str:
            continue

        results.append(
            ProductSimilarity(
                article_id=str(aid),
                score=float(s),
            )
        )

        if len(results) >= payload.N:
            break

    return results
