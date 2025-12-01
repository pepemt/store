"""Script de smoke-test para confirmar escritura de artefactos en MinIO via MLflow."""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import mlflow
from dotenv import load_dotenv
from mlflow.tracking import MlflowClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

LOCAL_MLFLOW_DIR = Path(
    os.getenv("LOCAL_MLFLOW_DIR", PROJECT_ROOT / "src" / "models" / "mlruns")
).resolve()

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


def _default_local_tracking_uri() -> str:
    LOCAL_MLFLOW_DIR.mkdir(parents=True, exist_ok=True)
    return f"file:{LOCAL_MLFLOW_DIR}"


def _get_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"La variable de entorno {name} es obligatoria y no está definida")
    return value  # type: ignore[return-value]


def _configure_s3_credentials_for_mlflow() -> None:
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


def _configure_mlflow_tracking() -> str:
    _configure_s3_credentials_for_mlflow()

    tracking_uri = _get_env("MLFLOW_TRACKING_URI", _default_local_tracking_uri())
    mlflow.set_tracking_uri(tracking_uri)

    registry_uri = os.getenv("MLFLOW_REGISTRY_URI")
    if registry_uri:
        mlflow.set_registry_uri(registry_uri)

    experiment_name = _get_env("MLFLOW_EXPERIMENT_NAME", "Default")
    artifact_root = os.getenv("MLFLOW_DEFAULT_ARTIFACT_ROOT") or None

    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        client.create_experiment(experiment_name, artifact_location=artifact_root)

    mlflow.set_experiment(experiment_name)
    return experiment_name


def main() -> None:
    experiment = _configure_mlflow_tracking()
    run_name = os.getenv("MINIO_TEST_RUN_NAME", "minio-connection-test")
    stamp = datetime.now(timezone.utc).isoformat()
    payload = f"MinIO connectivity test @ {stamp}"

    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_param("minio_test_timestamp", stamp)
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "minio-test.txt"
            test_file.write_text(payload, encoding="utf-8")
            mlflow.log_artifact(str(test_file), artifact_path="minio-test")

        print("Registro exitoso")
        print(f" Experimento: {experiment}")
        print(f" Run ID: {run.info.run_id}")
        print(f" Tracking URI: {mlflow.get_tracking_uri()}")
        print(f" Artifact URI: {run.info.artifact_uri}")


if __name__ == "__main__":
    main()
