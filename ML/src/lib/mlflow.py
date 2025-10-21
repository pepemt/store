import mlflow
from mlflow.tracking import MlflowClient
import os
from dotenv import load_dotenv

load_dotenv(".env")

class MlflowHandler:
    def __init__(self):
        self.client = MlflowClient(
            tracking_uri=os.getenv("MLFLOW_TRACKING_URI"),
            registry_uri=os.getenv("MLFLOW_REGISTRY_URI"),
        )
        mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT_NAME"))

    def register(self, model_path: str, model_name: str) -> str:
        result = mlflow.register_model(model_uri=model_path, name=model_name)
        return result.name

    def download(self, model_name: str, stage: str = "Staging"):
        model_uri = f"models:/{model_name}/{stage}"
        return mlflow.pyfunc.load_model(model_uri)

    def list_models(self) -> list:
        return [m.name for m in self.client.list_registered_models()]
