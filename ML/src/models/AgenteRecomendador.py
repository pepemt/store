"""Interfaz ligera para que un agente consuma el modelo ALS registrado en MLflow."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional

import mlflow
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

def _configure_s3_env() -> None:
    """Configura variables AWS para que boto3 use OCI Object Storage cuando se suban artifacts."""

    # Las variables ya deberían estar configuradas en .env
    # Esta función solo verifica que estén presentes
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION", "us-chicago-1")
    endpoint = os.getenv("MLFLOW_S3_ENDPOINT_URL")

    if not access_key:
        raise ValueError("AWS_ACCESS_KEY_ID no está configurada en las variables de entorno")
    if not secret_key:
        raise ValueError("AWS_SECRET_ACCESS_KEY no está configurada en las variables de entorno")
    if not endpoint:
        raise ValueError("MLFLOW_S3_ENDPOINT_URL no está configurada en las variables de entorno")

    # Asegurar que las variables estén en el ambiente
    if region and not os.getenv("AWS_DEFAULT_REGION"):
        os.environ["AWS_DEFAULT_REGION"] = region

_configure_s3_env()

def _resolve_tracking_uri() -> None:
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)

    registry_uri = os.getenv("MLFLOW_REGISTRY_URI")
    if registry_uri:
        mlflow.set_registry_uri(registry_uri)

@lru_cache(maxsize=1)
def _load_model(model_uri: Optional[str] = None):
    uri = model_uri or os.getenv("MLFLOW_MODEL_URI")
    if not uri:
        raise RuntimeError(
            "Define MLFLOW_MODEL_URI en el .env o pásalo como argumento para cargar el modelo registrado"
        )

    _resolve_tracking_uri()
    return mlflow.pyfunc.load_model(uri)

def obtener_recomendaciones(
    customer_ids: Iterable[str],
    n: int = 10,
    model_uri: Optional[str] = None,
) -> pd.DataFrame:
    """Devuelve recomendaciones para los customer_ids indicados.

    Args:
        customer_ids: IDs de clientes tal como están en el dataset original.
        n: Número de artículos que se desea para cada cliente.
        model_uri: URI de MLflow (runs:/..., models:/...). Si no se proporciona
            se toma la variable MLFLOW_MODEL_URI del entorno.
    """

    customer_ids = [str(cid) for cid in customer_ids]
    if not customer_ids:
        return pd.DataFrame(columns=["user_id", "article_id", "score"])

    model = _load_model(model_uri)
    payload = pd.DataFrame({"user_id": customer_ids, "N": n})
    predictions = model.predict(payload)
    return predictions

if __name__ == "__main__":
    ejemplo_cliente = os.getenv("EXAMPLE_CUSTOMER_ID")
    if not ejemplo_cliente:
        raise RuntimeError(
            "Define EXAMPLE_CUSTOMER_ID en el entorno para ejecutar el ejemplo o importa la función"
        )
    df = obtener_recomendaciones([ejemplo_cliente])
    print(df.head())
    df.to_csv("recomendaciones_ejemplo.csv", index=False)
