import os
from pathlib import Path
from typing import List, Optional, Union

import mlflow
from mlflow.tracking import MlflowClient
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILES = [PROJECT_ROOT / ".env", PROJECT_ROOT / "ML" / ".env"]


def _load_environment() -> None:
    """Carga variables de entorno desde archivos .env conocidos (si existen)."""
    for env_file in ENV_FILES:
        if env_file.exists():
            load_dotenv(env_file, override=False)  # no pisa valores ya exportados


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        searched = ", ".join(str(p) for p in ENV_FILES)
        raise RuntimeError(f"Missing environment variable {key}; checked: {searched}")
    return value


class MlflowHandler:
    """
    Wrapper mínimo y compatible con MLflow 3.x para:
      - fijar URIs de tracking/registry
      - registrar modelos y (opcional) asignar alias
      - cargar por alias/versión (y, sólo si es necesario, por stage)
      - listar y eliminar modelos
    """

    def __init__(self):
        _load_environment()

        tracking_uri = _require_env("MLFLOW_TRACKING_URI")
        experiment_name = _require_env("MLFLOW_EXPERIMENT_NAME")

        # En MLflow 3 el registry por defecto puede apuntar a Unity Catalog (databricks-uc).
        # Si usas otro backend (OSS, Workspace Registry, etc.), fija MLFLOW_REGISTRY_URI
        # o ajusta explícitamente aquí.
        registry_uri = os.getenv("MLFLOW_REGISTRY_URI")  # opcional

        mlflow.set_tracking_uri(tracking_uri)
        if registry_uri:
            mlflow.set_registry_uri(registry_uri)

        # Nota: el cliente ya no recibe registry_uri; se fija globalmente arriba.
        self.client = MlflowClient(tracking_uri=tracking_uri)
        mlflow.set_experiment(experiment_name)

    # ---------- Registro ----------

    def register(
        self,
        model_uri: str,
        model_name: str,
        *,
        alias: Optional[str] = None,
        await_creation: bool = True,
    ) -> str:
        """
        Registra un modelo previamente logueado (p.ej. runs:/<run_id>/model)
        y opcionalmente asigna un alias (p.ej. 'staging', 'champion').

        Returns: 'name/version' (p.ej. 'my_model/7')
        """
        mv = mlflow.register_model(model_uri=model_uri, name=model_name)
        version = mv.version

        if await_creation:
            # Espera a que el estado del artifact sea 'READY'
            self.client.get_model_version_download_uri(model_name, version)

        if alias:
            # Asigna/actualiza alias mutable (preferido vs stages en MLflow 3)
            self.client.set_registered_model_alias(model_name, alias, version)

        return f"{model_name}/{version}"

    # ---------- Carga ----------

    def load(
        self,
        model_name: str,
        *,
        alias: Optional[str] = None,
        version: Optional[Union[int, str]] = None,
        stage: Optional[str] = None,  # Deprecated en MLflow 3 (mantengo por compatibilidad)
        flavor: str = "pyfunc",
    ):
        """
        Carga un modelo desde el registry.

        Prioridad: alias > versión > stage > latest
        """
        if alias:
            model_uri = f"models:/{model_name}@{alias}"
        elif version is not None:
            model_uri = f"models:/{model_name}/{version}"
        elif stage:
            # Aviso suave: stages están deprecados en MLflow 3 (usa aliases).
            import warnings
            warnings.warn(
                "Model stages are deprecated in MLflow 3; prefer using aliases.",
                DeprecationWarning,
                stacklevel=2,
            )
            model_uri = f"models:/{model_name}/{stage}"
        else:
            # 'latest' depende del backend; considera usar alias para despliegues estables.
            model_uri = f"models:/{model_name}/latest"

        if flavor == "pyfunc":
            return mlflow.pyfunc.load_model(model_uri)
        # Puedes extender a sabores específicos: sklearn, pytorch, etc.
        return mlflow.pyfunc.load_model(model_uri)

    # ---------- Administración ----------

    def delete_model(self, model_name: str) -> None:
        self.client.delete_registered_model(name=model_name)

    def list_models(self) -> List[str]:
        # search_registered_models es el camino recomendado en 3.x
        rms = self.client.search_registered_models()
        return [rm.name for rm in rms]

    def set_alias(self, model_name: str, alias: str, version: Union[int, str]) -> None:
        """Atajo para gestionar aliases."""
        self.client.set_registered_model_alias(model_name, alias, str(version))

    def delete_alias(self, model_name: str, alias: str) -> None:
        self.client.delete_registered_model_alias(model_name, alias)