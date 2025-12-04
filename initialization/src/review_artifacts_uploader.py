"""
Uploader for review ML artifacts to MLflow.

Uploads:
- review_embeddings_qwen2.npy
- df_with_clusters_qwen2.pk1
- faiss_reviews_qwen2.index
"""

import os
import logging
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Constants
EXPERIMENT_NAME = "review-search-artifacts"
RUN_NAME = "review-artifacts-v1"
ARTIFACT_FILES = [
    "review_embeddings_qwen2.npy",
    "df_with_clusters_qwen2.pk1",
    "faiss_reviews_qwen2.index",
    "review_scoring_weights.json",
]


def _load_mlflow_config():
    """Load MLflow configuration from environment."""
    load_dotenv()

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        raise RuntimeError("MLFLOW_TRACKING_URI not set")

    mlflow.set_tracking_uri(tracking_uri)

    registry_uri = os.getenv("MLFLOW_REGISTRY_URI")
    if registry_uri:
        mlflow.set_registry_uri(registry_uri)

    # Configure S3/MinIO credentials for boto3 (used by MLflow for artifact storage)
    s3_access_key = os.getenv("MLFLOW_S3_ACCESS_KEY_ID")
    s3_secret_key = os.getenv("MLFLOW_S3_SECRET_ACCESS_KEY")
    s3_endpoint = os.getenv("MLFLOW_S3_ENDPOINT_URL")

    if s3_access_key:
        os.environ["AWS_ACCESS_KEY_ID"] = s3_access_key
    if s3_secret_key:
        os.environ["AWS_SECRET_ACCESS_KEY"] = s3_secret_key
    if s3_endpoint:
        os.environ["MLFLOW_S3_ENDPOINT_URL"] = s3_endpoint

    return tracking_uri


def _artifacts_already_uploaded(client: MlflowClient) -> bool:
    """Check if artifacts have already been uploaded."""
    try:
        experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
        if experiment is None:
            return False

        # Search for the specific run
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string=f"tags.mlflow.runName = '{RUN_NAME}'",
            max_results=1,
        )

        if not runs:
            return False

        # Check if all artifacts exist
        run = runs[0]
        artifacts = client.list_artifacts(run.info.run_id)
        artifact_names = {a.path for a in artifacts}

        return all(f in artifact_names for f in ARTIFACT_FILES)

    except Exception as e:
        logger.warning(f"Error checking existing artifacts: {e}")
        return False


def upload_review_artifacts_to_mlflow(artifacts_dir: str = ".data/reviews") -> None:
    """
    Upload review ML artifacts to MLflow.

    Args:
        artifacts_dir: Directory containing the artifact files
    """
    artifacts_path = Path(artifacts_dir)

    # Verify all files exist
    missing = []
    for filename in ARTIFACT_FILES:
        if not (artifacts_path / filename).exists():
            missing.append(filename)

    if missing:
        logger.warning(f"Missing artifact files, skipping upload: {missing}")
        return

    # Configure MLflow
    tracking_uri = _load_mlflow_config()
    client = MlflowClient(tracking_uri=tracking_uri)

    # Check if already uploaded
    if _artifacts_already_uploaded(client):
        logger.info("Review artifacts already uploaded to MLflow, skipping...")
        return

    # Create/set experiment
    mlflow.set_experiment(EXPERIMENT_NAME)

    # Upload artifacts
    logger.info(f"Uploading review artifacts to MLflow experiment '{EXPERIMENT_NAME}'...")

    with mlflow.start_run(run_name=RUN_NAME):
        for filename in ARTIFACT_FILES:
            file_path = artifacts_path / filename
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"  Uploading {filename} ({file_size_mb:.1f} MB)...")
            mlflow.log_artifact(str(file_path))

        # Log some metadata
        mlflow.log_param("artifact_count", len(ARTIFACT_FILES))
        mlflow.log_param("source_dir", str(artifacts_path.absolute()))

    logger.info("Review artifacts uploaded successfully to MLflow.")


def get_artifact_download_path(client: MlflowClient = None) -> str:
    """
    Get the download path for review artifacts from MLflow.

    Returns:
        Path to the artifacts in MLflow storage
    """
    if client is None:
        tracking_uri = _load_mlflow_config()
        client = MlflowClient(tracking_uri=tracking_uri)

    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        raise RuntimeError(f"Experiment '{EXPERIMENT_NAME}' not found")

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string=f"tags.mlflow.runName = '{RUN_NAME}'",
        max_results=1,
    )

    if not runs:
        raise RuntimeError(f"Run '{RUN_NAME}' not found in experiment '{EXPERIMENT_NAME}'")

    return runs[0].info.artifact_uri
