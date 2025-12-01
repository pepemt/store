from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import mlflow

# =========================
#  CONFIGURACIÓN MLFLOW
# =========================

# Deducción del PROJECT_ROOT asumiendo que este archivo vive en: store/api/src
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MODEL_URI = "runs:/51eecff67e2a4bfa9c5637708ca1303b/model"
MLFLOW_MODEL_URI = os.getenv("MLFLOW_MODEL_URI", DEFAULT_MODEL_URI)


def _configure_s3_env() -> None:
    """Propagate MinIO credentials so mlflow/boto can reach the artifact store."""

    mappings = {
        "MLFLOW_S3_ACCESS_KEY_ID": "AWS_ACCESS_KEY_ID",
        "MLFLOW_S3_SECRET_ACCESS_KEY": "AWS_SECRET_ACCESS_KEY",
        "MLFLOW_S3_REGION": "AWS_DEFAULT_REGION",
    }

    for source, target in mappings.items():
        value = os.getenv(source)
        if value and not os.getenv(target):
            os.environ[target] = value

    endpoint = os.getenv("MLFLOW_S3_ENDPOINT_URL")
    if endpoint:
        os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", endpoint)


def _resolve_tracking_uri() -> str:
    """Return tracking URI, preferring env var and falling back to local folder."""
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        raise RuntimeError(
            "MLFLOW_TRACKING_URI debe estar definido para acceder al servidor remoto"
        )
    return tracking_uri


def _configure_mlflow() -> None:
    _configure_s3_env()
    tracking_uri = _resolve_tracking_uri()
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_registry_uri(tracking_uri)


@lru_cache(maxsize=1)
def get_model():
    _configure_mlflow()
    try:
        model = mlflow.pyfunc.load_model(MLFLOW_MODEL_URI)
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo cargar el modelo desde '{MLFLOW_MODEL_URI}': {exc}"
        ) from exc
    return model
