from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from products_model import router as products_router

import mlflow
import pandas as pd

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# =========================
#  CONFIGURACIÓN MLFLOW
# =========================

# Deducción del PROJECT_ROOT asumiendo que este archivo vive en: store/api/src/ml.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]

LOCAL_MLFLOW_DIR = Path(
    os.getenv("LOCAL_MLFLOW_DIR", PROJECT_ROOT / "src" / "models" / "mlruns")
).resolve()

DEFAULT_MODEL_URI = "runs:/439bdc0a9c71484f8f090eb39128afa1/model"
MLFLOW_MODEL_URI = os.getenv("MLFLOW_MODEL_URI", DEFAULT_MODEL_URI)


def _configure_mlflow() -> None:

    tracking_uri = f"file:{LOCAL_MLFLOW_DIR}"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_registry_uri(tracking_uri)


@lru_cache(maxsize=1)
def get_model():

    _configure_mlflow()
    try:
        model = mlflow.pyfunc.load_model(MLFLOW_MODEL_URI)
    except Exception as exc:  
        raise RuntimeError(f"No se pudo cargar el modelo desde '{MLFLOW_MODEL_URI}': {exc}") from exc
    return model


class RecommendRequest(BaseModel):
    user_id: str
    N: int = 10


class Recommendation(BaseModel):
    user_id: str
    article_id: str
    score: float



app = FastAPI(
    title="ALS Recommender API",
    version="1.0.0",
    description="API para consumir el modelo ALS de recomendaciones registrado en MLflow (todo local).",
)


app.include_router(products_router)
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def root() -> dict:
    return {"message": "ALS Recommender API funcionando", "model_uri": MLFLOW_MODEL_URI}


@app.post("/recommend", response_model=List[Recommendation])
def recommend(payload: RecommendRequest) -> List[Recommendation]:
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

    recommendations: List[Recommendation] = []
    for _, row in recs_df.iterrows():
        recommendations.append(
            Recommendation(
                user_id=str(row["user_id"]),
                article_id=str(row["article_id"]),
                score=float(row["score"]),
            )
        )

    return recommendations


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "transactions_model:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
