import mlflow
import pandas as pd
from pathlib import Path

LOCAL_MLFLOW_DIR = Path("/Users/yosesotomayor/Code/store/ML/src/models/mlruns").resolve()
mlflow.set_tracking_uri(f"file:{LOCAL_MLFLOW_DIR}")

model_uri = "runs:/439bdc0a9c71484f8f090eb39128afa1/model"

model = mlflow.pyfunc.load_model(model_uri)

df_input = pd.DataFrame(
    [
        {
            "user_id": "00000dbacae5abe5e23885899a1fa44253a17956c6d1c3d25f88aa139fdfc657",
            "N": 10,
        }
    ]
)

recs = model.predict(df_input)
print(recs.head())