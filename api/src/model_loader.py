from __future__ import annotations

import logging
import os
from pathlib import Path

import mlflow

logger = logging.getLogger(__name__)

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
    return os.getenv("MLFLOW_TRACKING_URI", f"file:{LOCAL_MLFLOW_DIR}")


def _configure_mlflow() -> None:
    _configure_s3_env()
    tracking_uri = _resolve_tracking_uri()
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_registry_uri(tracking_uri)


# Variable global para el modelo precargado
_model = None


def get_model():
    """Obtiene el modelo. Si no está precargado, lo carga ahora."""
    global _model
    if _model is None:
        _model = _load_model()
    return _model


def _load_model():
    """Carga el modelo desde MLflow."""
    _configure_mlflow()
    try:
        logger.info(f"Cargando modelo desde: {MLFLOW_MODEL_URI}")
        model = mlflow.pyfunc.load_model(MLFLOW_MODEL_URI)
        logger.info("Modelo cargado exitosamente")
        return model
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo cargar el modelo desde '{MLFLOW_MODEL_URI}': {exc}"
        ) from exc


async def preload_model():
    """
    Precarga el modelo de forma asíncrona durante el startup.
    Esto evita que la primera petición tenga que esperar la descarga.
    """
    global _model
    if _model is not None:
        logger.info("Modelo ya está cargado, saltando precarga")
        return

    import asyncio
    import concurrent.futures

    logger.info("Iniciando precarga del modelo ML en segundo plano...")

    # Ejecutar la carga en un thread pool para no bloquear el event loop
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            _model = await loop.run_in_executor(pool, _load_model)
            logger.info("Modelo ML precargado exitosamente")
        except Exception as e:
            logger.error(f"Error al precargar modelo ML: {e}")
            # No lanzar excepción - el modelo se cargará cuando se necesite
