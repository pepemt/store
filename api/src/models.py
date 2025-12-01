from __future__ import annotations

import os
from typing import List

import pandas as pd

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from model_loader import MLFLOW_MODEL_URI, get_model
from products_model import router as products_router


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
    description=".",
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

# que loco estimado 
