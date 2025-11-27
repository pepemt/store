"""Entrena un modelo ALS de recomendaciones y lo registra en MLflow."""
from __future__ import annotations

import warnings
import json
import os
import pickle
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple
from urllib.parse import unquote

import mlflow
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from implicit.als import AlternatingLeastSquares
from pyspark.sql import DataFrame, SparkSession
from scipy.sparse import coo_matrix, csr_matrix

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT.parent / ".env"

warnings.filterwarnings("ignore", category=UserWarning,module="pyspark")
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

LOCAL_MLFLOW_DIR = Path(
    os.getenv("LOCAL_MLFLOW_DIR", PROJECT_ROOT / "src" / "models" / "mlruns")
).resolve()

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.main import _ensure_java_home  # noqa: E402


def _default_local_tracking_uri() -> str:
    """Devuelve un file:// URI al directorio local de mlruns y lo crea si falta."""

    LOCAL_MLFLOW_DIR.mkdir(parents=True, exist_ok=True)
    return f"file:{LOCAL_MLFLOW_DIR}"


@dataclass
class RecommenderArtifacts:
    model: AlternatingLeastSquares
    customer_map: Dict[str, int]
    article_map: Dict[str, int]
    interaction_matrix: csr_matrix

    def recommend(self, customer_id: str, n: int = 10) -> pd.DataFrame:
        inv_article_map = {v: k for k, v in self.article_map.items()}
        idx = self.customer_map.get(customer_id)
        if idx is None:
            raise ValueError(f"Cliente {customer_id} no existe en el mapa de clientes")

        recs = self.model.recommend(
            idx,
            self.interaction_matrix[idx],
            N=n,
            recalculate_user=True,
            filter_already_liked_items=True,
        )

        if isinstance(recs, tuple):
            item_indices, scores = recs
        else:
            item_indices = [item for item, _ in recs]
            scores = [score for _, score in recs]

        recommended_article_ids = [inv_article_map[int(i)] for i in item_indices]
        return pd.DataFrame({"article_id": recommended_article_ids, "score": scores})


def _get_env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"La variable de entorno {name} es obligatoria y no está definida")
    return value  # type: ignore[return-value]


def build_spark_session() -> SparkSession:
    _ensure_java_home()

    spark_app_name = _get_env("SPARK_APP_NAME", "als-recommender")
    spark_master_url = _get_env("SPARK_MASTER_URL", "local[*]")
    driver_memory = _get_env("SPARK_DRIVER_MEMORY", "6g")
    driver_max_result = _get_env("SPARK_DRIVER_MAX_RESULT_SIZE", "4g")
    executor_memory = _get_env("SPARK_EXECUTOR_MEMORY")

    builder = (
        SparkSession.builder.appName(spark_app_name)
        .master(spark_master_url)
        .config("spark.jars.packages", "org.postgresql:postgresql:42.7.8")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.driver.memory", driver_memory)
        .config("spark.driver.maxResultSize", driver_max_result)
    )

    if executor_memory:
        builder = builder.config("spark.executor.memory", executor_memory)

    return builder.getOrCreate()


def read_table(spark: SparkSession, table: str) -> DataFrame:
    print(f"Leyendo tabla {table} desde Postgres")
    postgres_url = _get_env("SPARK_DATABASE_URL", required=True)
    postgres_user = _get_env("SPARK_DATABASE_USER", required=True)
    postgres_password = _get_env("SPARK_DATABASE_PASSWORD", required=True)

    postgres_password = unquote(postgres_password)

    reader = spark.read.format("jdbc")
    options = {
        "url": postgres_url,
        "dbtable": table,
        "user": postgres_user,
        "password": postgres_password,
        "driver": "org.postgresql.Driver",
    }

    for key, value in options.items():
        reader = reader.option(key, value)

    return reader.load()


def load_transactions(csv_path: Optional[str], allowed_customers: Iterable[str], allowed_articles: Iterable[str]) -> pd.DataFrame:
    resolved = Path(csv_path or "").expanduser() if csv_path else None
    if not resolved or not resolved.exists():
        raise FileNotFoundError(
            "No se encontró el archivo de transacciones. Define TRANSACTIONS_CSV_PATH en el .env"
        )

    print(f"Leyendo archivo {resolved}")

    df = pd.read_csv(resolved, usecols=["customer_id", "article_id"])
    df = df.dropna(subset=["customer_id", "article_id"])
    df["customer_id"] = df["customer_id"].astype(str)
    df["article_id"] = df["article_id"].astype(str)

    allowed_customers = set(str(cid) for cid in allowed_customers)
    allowed_articles = set(str(aid) for aid in allowed_articles)

    df = df[df["customer_id"].isin(allowed_customers)]
    df = df[df["article_id"].isin(allowed_articles)]
    return df


def build_interaction_matrix(transactions: pd.DataFrame, article_ids: Iterable[str]) -> Tuple[csr_matrix, Dict[str, int], Dict[str, int]]:
    transactions = transactions.copy()
    transactions.set_index("customer_id", inplace=True)

    unique_customers = transactions.index.unique().tolist()
    customer_map = {str(cid): idx for idx, cid in enumerate(unique_customers)}

    article_ids = [str(aid) for aid in article_ids]
    article_map = {aid: idx for idx, aid in enumerate(article_ids)}

    transactions.reset_index(inplace=True)
    transactions = transactions[transactions["article_id"].isin(article_map)]

    rows = transactions["customer_id"].map(customer_map).to_numpy()
    cols = transactions["article_id"].map(article_map).to_numpy()
    data = np.ones(len(transactions), dtype=np.float32)

    interaction = coo_matrix((data, (rows, cols)), shape=(len(customer_map), len(article_map))).tocsr()
    return interaction, customer_map, article_map


def train_model(interaction_matrix: csr_matrix) -> AlternatingLeastSquares:
    model = AlternatingLeastSquares(factors=50, regularization=0.1, iterations=15)
    model.fit(interaction_matrix)
    return model


class ALSWrapper(mlflow.pyfunc.PythonModel):
    def load_context(self, context):  # type: ignore[override]
        with open(context.artifacts["als_model"], "rb") as f:
            self.model = pickle.load(f)
        with open(context.artifacts["user_map"], "r") as f:
            self.user_map = json.load(f)
        with open(context.artifacts["item_map"], "r") as f:
            self.item_map = json.load(f)
        self.rev_item_map = {int(v): k for k, v in self.item_map.items()}
        with open(context.artifacts["interaction_csr"], "rb") as f:
            self.interaction_matrix = pickle.load(f)

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:  # type: ignore[override]
        results = []
        for _, row in model_input.iterrows():
            user_id = str(row["user_id"])
            top_n = int(row.get("N", 10))
            if user_id not in self.user_map:
                continue
            user_idx = int(self.user_map[user_id])
            recs = self.model.recommend(
                user_idx,
                user_items=self.interaction_matrix[user_idx],
                N=top_n,
                filter_already_liked_items=True,
            )
            if isinstance(recs, tuple):
                item_indices, scores = recs
            else:
                item_indices = [item for item, _ in recs]
                scores = [score for _, score in recs]

            for article_idx, score in zip(item_indices, scores):
                results.append(
                    {
                        "user_id": user_id,
                        "article_id": self.rev_item_map.get(int(article_idx), int(article_idx)),
                        "score": float(score),
                    }
                )
        return pd.DataFrame(results)


def log_model_to_mlflow(artifacts: RecommenderArtifacts, run_name: str = "als recomendaciones") -> Tuple[str, str]:
    # Forzamos todo a ser completamente local usando un backend file:// en LOCAL_MLFLOW_DIR
    tracking_uri = _default_local_tracking_uri()
    experiment_name = _get_env("MLFLOW_EXPERIMENT_NAME", "Default")

    mlflow.set_tracking_uri(tracking_uri)
    # Usar el mismo backend local para el registry (sin S3 / MinIO)
    mlflow.set_registry_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(
            {
                "factors": artifacts.model.factors,
                "regularization": artifacts.model.regularization,
                "iterations": artifacts.model.iterations,
                "num_customers": len(artifacts.customer_map),
                "num_articles": len(artifacts.article_map),
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.pkl"
            user_map_path = Path(tmp) / "user_map.json"
            item_map_path = Path(tmp) / "item_map.json"
            interaction_path = Path(tmp) / "interaction.pkl"

            with open(model_path, "wb") as f:
                pickle.dump(artifacts.model, f)
            with open(user_map_path, "w") as f:
                json.dump(artifacts.customer_map, f)
            with open(item_map_path, "w") as f:
                json.dump(artifacts.article_map, f)
            with open(interaction_path, "wb") as f:
                pickle.dump(artifacts.interaction_matrix, f)

            mlflow.pyfunc.log_model(
                artifact_path="model",
                python_model=ALSWrapper(),
                artifacts={
                    "als_model": str(model_path),
                    "user_map": str(user_map_path),
                    "item_map": str(item_map_path),
                    "interaction_csr": str(interaction_path),
                },
                pip_requirements=["mlflow>=3.0.0", "implicit>=0.7", "pandas", "numpy", "scipy"],
            )

        model_uri = f"runs:/{run.info.run_id}/model"
        return run.info.run_id, model_uri


def train_and_log() -> Tuple[RecommenderArtifacts, str]:
    spark = build_spark_session()
    articles_pdf = read_table(spark, "articles").toPandas()
    print(f"Tabla articles cargada: {articles_pdf.shape[0]} filas")
    customers_pdf = read_table(spark, "customers").toPandas()
    print(f"Tabla customers cargada: {customers_pdf.shape[0]} filas")

    transactions_path = _get_env("TRANSACTIONS_CSV_PATH", default=None)
    transactions_pdf = load_transactions(
        transactions_path,
        allowed_customers=customers_pdf["customer_id"].astype(str),
        allowed_articles=articles_pdf["article_id"].astype(str),
    )
    print(f"Transacciones cargadas: {transactions_pdf.shape[0]} filas")

    interaction, customer_map, article_map = build_interaction_matrix(
        transactions_pdf, articles_pdf["article_id"].astype(str)
    )
    print(
        f"Matriz construida: {interaction.shape[0]} clientes x {interaction.shape[1]} artículos"
    )

    model = train_model(interaction)
    print("Entrenamiento terminado")
    artifacts = RecommenderArtifacts(model, customer_map, article_map, interaction)
    _, model_uri = log_model_to_mlflow(artifacts)
    return artifacts, model_uri

def recomendacion_item_based(artifacts: RecommenderArtifacts, article_id: str, n: int = 10) -> pd.DataFrame:
    """
    Recomienda artículos similares a un artículo dado usando el modelo ALS entrenado.
  
    Parameters
    ----------
    artifacts : RecommenderArtifacts
        Artefactos del modelo (incluye article_map y modelo ALS).
    article_id : str
        Identificador del artículo de referencia.
    n : int
        Número de artículos similares a devolver.
  
    Returns
    -------
    pd.DataFrame
        DataFrame con columnas ["article_id", "score"] ordenado por similitud.
    """
    inv_article_map = {v: k for k, v in artifacts.article_map.items()}
    idx = artifacts.article_map.get(str(article_id))
    if idx is None:
        raise ValueError(f"Artículo {article_id} no existe en el mapa de artículos")
  
    # similar_items suele incluir al propio artículo como el más parecido, así que pedimos n+1
    recs = artifacts.model.similar_items(idx, N=n + 1)
  
    if isinstance(recs, tuple):
        item_indices, scores = recs
    else:
        item_indices = [item for item, _ in recs]
        scores = [score for _, score in recs]
  
    similar_article_ids = []
    similar_scores = []
    for i, s in zip(item_indices, scores):
        aid = inv_article_map.get(int(i))
        # Excluir el artículo de entrada
        if aid is None or aid == str(article_id):
            continue
        similar_article_ids.append(aid)
        similar_scores.append(float(s))
        if len(similar_article_ids) >= n:
            break
  
    return pd.DataFrame({"article_id": similar_article_ids, "score": similar_scores})

def main():
    artifacts, model_uri = train_and_log()
    print(f"Modelo registrado en: {model_uri}")
    sample_customer = next(iter(artifacts.customer_map))
    preview = artifacts.recommend(sample_customer).head()
    print("Vista previa de recomendaciones:")
    print(preview)
    sample_article = next(iter(artifacts.article_map))
    similar_preview = recomendacion_item_based(artifacts, sample_article).head()
    print(f"Vista previa de artículos similares a {sample_article}:")
    print(similar_preview)


if __name__ == "__main__":
    main()
