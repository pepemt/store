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
        raise RuntimeError(
            f"No se pudo cargar el modelo desde '{MLFLOW_MODEL_URI}': {exc}"
        ) from exc
    return model
