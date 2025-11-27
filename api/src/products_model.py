

from __future__ import annotations

from typing import List

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Reutilizamos la lógica de carga del modelo definida en src/ml.py
from src.ml import get_model

router = APIRouter(
    prefix="/products",
    tags=["products"],
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
#  ENDPOINTS
# =========================

@router.post("/recommend/user", response_model=List[UserRecommendation])
def recommend_for_user(payload: UserRecommendRequest) -> List[UserRecommendation]:
    """
    Devuelve recomendaciones de productos para un usuario,
    usando el modelo ALS (user-based) registrado en MLflow.
    """
    model = get_model()

    df_input = pd.DataFrame(
        [
            {
                "user_id": payload.user_id,
                "N": payload.N,
            }
        ]
    )

    try:
        recs_df = model.predict(df_input)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al generar recomendaciones: {exc}")

    if recs_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron recomendaciones para el usuario {payload.user_id}",
        )

    results: List[UserRecommendation] = []
    for _, row in recs_df.iterrows():
        results.append(
            UserRecommendation(
                user_id=str(row["user_id"]),
                article_id=str(row["article_id"]),
                score=float(row["score"]),
            )
        )

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
        raise HTTPException(
            status_code=404,
            detail=f"Artículo {article_id_str} no existe en el mapa de artículos.",
        )

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

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron artículos similares para {article_id_str}",
        )

    return results