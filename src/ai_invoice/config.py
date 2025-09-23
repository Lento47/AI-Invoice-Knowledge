import os
from dataclasses import dataclass


@dataclass
class Settings:
    classifier_path: str = os.getenv("CLASSIFIER_PATH", "models/classifier.joblib")
    predictive_path: str = os.getenv("PREDICTIVE_PATH", "models/predictive.joblib")


settings = Settings()
