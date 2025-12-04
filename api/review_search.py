
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

import faiss
import numpy as np
import pandas as pd
from sqlalchemy import select

from database.lib import Database
from database.models import Article, Transaction
from text.embeddings import EmbeddingModel

logger = logging.getLogger(__name__)

# Default scoring weights (used if weights file not available)
DEFAULT_TOP_SIMILARITY_WEIGHT = 0.6
DEFAULT_AVG_SIMILARITY_WEIGHT = 0.4

# MLflow configuration for artifact download
MLFLOW_EXPERIMENT_NAME = "review-search-artifacts"
MLFLOW_RUN_NAME = "review-artifacts-v1"


def _download_artifacts_from_mlflow(local_dir: str, artifact_files: List[str]) -> bool:
    """
    Download review artifacts from MLflow (always fetches from MLflow).

    Args:
        local_dir: Local directory to store artifacts
        artifact_files: List of artifact filenames to download

    Returns:
        True if all artifacts are available, False otherwise
    """
    local_path = Path(local_dir)
    local_path.mkdir(parents=True, exist_ok=True)

    # Always download from MLflow to ensure consistency
    try:
        import mlflow
        from mlflow.tracking import MlflowClient
        from dotenv import load_dotenv

        load_dotenv()

        tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        if not tracking_uri:
            logger.warning("MLFLOW_TRACKING_URI not set, cannot download artifacts")
            return False

        # Configure S3/MinIO credentials for boto3
        s3_access_key = os.getenv("MLFLOW_S3_ACCESS_KEY_ID")
        s3_secret_key = os.getenv("MLFLOW_S3_SECRET_ACCESS_KEY")
        s3_endpoint = os.getenv("MLFLOW_S3_ENDPOINT_URL")
        if s3_access_key:
            os.environ["AWS_ACCESS_KEY_ID"] = s3_access_key
        if s3_secret_key:
            os.environ["AWS_SECRET_ACCESS_KEY"] = s3_secret_key
        if s3_endpoint:
            os.environ["MLFLOW_S3_ENDPOINT_URL"] = s3_endpoint

        mlflow.set_tracking_uri(tracking_uri)
        client = MlflowClient(tracking_uri=tracking_uri)

        # Find the experiment and run
        experiment = client.get_experiment_by_name(MLFLOW_EXPERIMENT_NAME)
        if experiment is None:
            logger.warning(f"MLflow experiment '{MLFLOW_EXPERIMENT_NAME}' not found")
            return False

        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string=f"tags.mlflow.runName = '{MLFLOW_RUN_NAME}'",
            max_results=1,
        )

        if not runs:
            logger.warning(f"MLflow run '{MLFLOW_RUN_NAME}' not found")
            return False

        run_id = runs[0].info.run_id
        logger.info(f"Downloading review artifacts from MLflow run {run_id}...")

        # Download each artifact (overwrite local files)
        for filename in artifact_files:
            local_file = local_path / filename
            if local_file.exists():
                local_file.unlink()  # Remove local file to force fresh download

            logger.info(f"  Downloading {filename} from MLflow...")
            try:
                mlflow.artifacts.download_artifacts(
                    run_id=run_id,
                    artifact_path=filename,
                    dst_path=str(local_path),
                )
            except Exception as e:
                logger.error(f"  Failed to download {filename}: {e}")
                return False

        logger.info("Review artifacts downloaded successfully from MLflow")
        return True

    except ImportError:
        logger.warning("MLflow not installed, cannot download artifacts")
        return False
    except Exception as e:
        logger.warning(f"Failed to download artifacts from MLflow: {e}")
        return False


def _build_images(article_id: int) -> List[str]:
    """Crea URL de imagen usando el proxy del backend."""
    backend_url = os.getenv("FASTAPI_PUBLIC_URL", "http://localhost:8000")
    padded_id = str(article_id).zfill(10)
    return [f"{backend_url}/api/v1/images/products/{padded_id}.jpg"]


async def _get_average_price(session, article_id: int) -> float:
    """Precio promedio; fallback determinístico si no hay transacciones."""
    try:
        stmt = select(Transaction.price).where(Transaction.article_id == article_id)
        prices = [row[0] for row in (await session.execute(stmt)).all()]
        if prices:
            return float(sum(prices) / len(prices))
    except Exception:
        pass
    base = 29.99
    return float(base + (article_id % 100))


class ReviewSearchEngine:
    """
    Motor de búsqueda por reviews.
    Carga embeddings + DF + índice FAISS y ofrece:
      - search_reviews: busca reviews similares a una necesidad
      - aggregate_products: agrupa por producto y calcula score
      - get_products: trae los datos de producto desde Postgres
    """

    def __init__(
        self,
        artifacts_dir: str = "api/artifacts/reviews",
        emb_file: str = "review_embeddings_qwen2.npy",
        df_file: str = "df_with_clusters_qwen2.pk1",
        index_file: str = "faiss_reviews_qwen2.index",
        weights_file: str = "review_scoring_weights.json",
        model_name: str = "Alibaba-NLP/gte-Qwen2-1.5B-instruct",
        use_mlflow: bool = True,
    ):
        self.artifacts_dir = artifacts_dir
        self.emb_file = emb_file
        self.df_file = df_file
        self.index_file = index_file
        self.weights_file = weights_file

        # Try to download artifacts from MLflow if enabled and not present locally
        if use_mlflow:
            artifact_files = [emb_file, df_file, index_file, weights_file]
            _download_artifacts_from_mlflow(artifacts_dir, artifact_files)

        self.emb_path = os.path.join(artifacts_dir, emb_file)
        self.df_path = os.path.join(artifacts_dir, df_file)
        self.index_path = os.path.join(artifacts_dir, index_file)
        self.weights_path = os.path.join(artifacts_dir, weights_file)
        self.model = EmbeddingModel(model_name=model_name, use_gpu=False)

        # Load scoring weights from MLflow artifact
        self.top_similarity_weight, self.avg_similarity_weight = self._load_weights()

        # Carga datos
        self.reviews_df = self._load_reviews()
        self.embeddings = self._load_embeddings()
        self.index = self._load_or_build_index()

    def _load_weights(self) -> Tuple[float, float]:
        """Load scoring weights from JSON file (downloaded from MLflow)."""
        if os.path.exists(self.weights_path):
            try:
                with open(self.weights_path, "r") as f:
                    config = json.load(f)
                weights = config.get("weights", {})
                top_w = weights.get("top_similarity_weight", DEFAULT_TOP_SIMILARITY_WEIGHT)
                avg_w = weights.get("avg_similarity_weight", DEFAULT_AVG_SIMILARITY_WEIGHT)
                logger.info(f"Loaded review scoring weights from MLflow: top={top_w}, avg={avg_w}")
                return float(top_w), float(avg_w)
            except Exception as e:
                logger.warning(f"Failed to load weights from {self.weights_path}: {e}")
        logger.info(f"Using default scoring weights: top={DEFAULT_TOP_SIMILARITY_WEIGHT}, avg={DEFAULT_AVG_SIMILARITY_WEIGHT}")
        return DEFAULT_TOP_SIMILARITY_WEIGHT, DEFAULT_AVG_SIMILARITY_WEIGHT

    def _load_reviews(self) -> pd.DataFrame:
        logger.info(f"Cargando reviews desde {self.df_path}")
        if self.df_path.endswith(".pk1") or self.df_path.endswith(".pkl"):
            return pd.read_pickle(self.df_path)
        if self.df_path.endswith(".csv"):
            return pd.read_csv(self.df_path)
        raise RuntimeError(f"Formato no soportado para reviews: {self.df_path}")

    def _load_embeddings(self) -> np.ndarray:
        logger.info(f"Cargando embeddings desde {self.emb_path}")
        emb = np.load(self.emb_path).astype("float32", copy=False)
        return emb

    def _load_or_build_index(self) -> faiss.IndexFlatIP:
        dim = self.embeddings.shape[1]
        if os.path.exists(self.index_path):
            logger.info(f"Cargando índice FAISS desde {self.index_path}")
            index = faiss.read_index(self.index_path)
            return index
        logger.info("Construyendo índice FAISS en memoria")
        index = faiss.IndexFlatIP(dim)
        emb_norm = self.embeddings.copy()
        faiss.normalize_L2(emb_norm)
        index.add(emb_norm)
        return index

    def search_reviews(self, query: str, top_k: int = 50) -> List[Dict[str, Any]]:
        """Devuelve reviews más similares a la necesidad del usuario."""
        query_emb = self.model.embed(query).astype("float32", copy=False)
        query_emb = query_emb.reshape(1, -1)  # 2D array required by FAISS
        faiss.normalize_L2(query_emb)

        scores, idxs = self.index.search(query_emb, k=min(top_k, len(self.embeddings)))
        scores = scores.flatten()
        idxs = idxs.flatten()

        results: List[Dict[str, Any]] = []
        for idx, score in zip(idxs, scores):
            row = self.reviews_df.iloc[int(idx)]
            results.append({
                "article_id": int(row.get("article_id") or row.get("product_code") or row.get("id")),
                "review": row.get("review") or row.get("review_text", ""),
                "review_stars": float(row.get("review_stars", 0)),
                "similarity": float(score),
            })
        return results

    def aggregate_products(self, review_hits: List[Dict[str, Any]]) -> List[Tuple[int, float, Dict[str, Any]]]:
        """Agrupa reviews por producto y calcula score final."""
        per_product: Dict[int, Dict[str, Any]] = {}
        for hit in review_hits:
            pid = hit["article_id"]
            sim = hit["similarity"]
            if pid not in per_product:
                per_product[pid] = {"score_sum": 0.0, "count": 0, "top_similarity": 0.0, "top_review": hit}
            per_product[pid]["score_sum"] += sim
            per_product[pid]["count"] += 1
            if sim > per_product[pid]["top_similarity"]:
                per_product[pid]["top_similarity"] = sim
                per_product[pid]["top_review"] = hit

        ranked: List[Tuple[int, float, Dict[str, Any]]] = []
        for pid, data in per_product.items():
            score = (data["top_similarity"] * self.top_similarity_weight +
                     (data["score_sum"] / data["count"]) * self.avg_similarity_weight)
            ranked.append((pid, score, data["top_review"]))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    async def get_products(self, ranked_products: List[Tuple[int, float, Dict[str, Any]]], limit: int = 10) -> List[Dict[str, Any]]:
        """Trae info de producto y adjunta snippet de review + score."""
        product_ids = [pid for pid, _, _ in ranked_products[:limit]]

        async with Database.get_session() as session:
            stmt = select(Article).where(Article.article_id.in_(product_ids))
            rows = (await session.execute(stmt)).scalars().all()
            articles = {a.article_id: a for a in rows}

            result: List[Dict[str, Any]] = []
            for pid, score, review_hit in ranked_products:
                if pid not in articles:
                    continue
                art = articles[pid]
                price = await _get_average_price(session, pid)
                result.append({
                    "id": art.article_id,
                    "name": art.prod_name,
                    "description": art.detail_desc,
                    "category": art.product_type_name,
                    "department": art.department_name,
                    "product_group": art.product_group_name,
                    "color": art.colour_group_name,
                    "price": price,
                    "images": _build_images(art.article_id),
                    "score": round(float(score), 3),
                    "evidence_review": review_hit.get("review", ""),
                    "from_reviews": True,
                })
                if len(result) >= limit:
                    break
            return result
