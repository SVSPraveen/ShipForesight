import joblib
import os
import pandas as pd
from backend.config import get_settings

class Predictor:
    def __init__(self):
        settings = get_settings()
        self.models_loaded = False
        
        # Load all 4 .pkl files exactly once at startup
        try:
            self.preprocessor = joblib.load(os.path.join(settings.models_dir, "preprocessor.pkl"))
            self.classifier = joblib.load(os.path.join(settings.models_dir, "classifier.pkl"))
            self.regressor = joblib.load(os.path.join(settings.models_dir, "regressor.pkl"))
            
            # The reason classifier was saved as a tuple: (Model, LabelEncoder)
            self.reason_clf, self.label_encoder = joblib.load(os.path.join(settings.models_dir, "reason_clf.pkl"))
            
            self.models_loaded = True
            print("All ML models loaded successfully.")
        except Exception as e:
            # Per the spec: Log a warning but do NOT raise. Set models_loaded = False.
            print(f"WARNING: Failed to load ML models. Run trainer.py first. Error: {e}")

    def predict(self, feature_df: pd.DataFrame) -> dict:
        """
        Takes a single-row feature DataFrame (from FeatureBuilder).
        Runs the ML pipeline and returns a structured dictionary containing:
        - delay_predicted: bool
        - raw_probability: float
        - estimated_delay_days: float
        - delay_reason: str
        """
        if not self.models_loaded:
            raise RuntimeError("ML models not loaded. Cannot run prediction.")
            
        # 1. Transform features using the loaded ColumnTransformer
        X = self.preprocessor.transform(feature_df)
        
        # 2. Stage 1: Ensemble Binary Classifier
        raw_probability = float(self.classifier.predict_proba(X)[0][1])
        delay_flag = bool(raw_probability >= 0.5)
        
        # 3. Conditional Stage 2 and Stage 3
        if delay_flag:
            # Stage 2: LightGBM Regressor (clamped to 0.0 and rounded to 1 decimal)
            estimated_delay_days = max(0.0, round(float(self.regressor.predict(X)[0]), 1))
            
            # Stage 3: Reason Classifier (decode label using LabelEncoder)
            reason_pred_encoded = self.reason_clf.predict(X)
            delay_reason = str(self.label_encoder.inverse_transform(reason_pred_encoded)[0])
        else:
            estimated_delay_days = 0.0
            delay_reason = ""
            
        return {
            "delay_predicted": delay_flag,
            "raw_probability": raw_probability,
            "estimated_delay_days": estimated_delay_days,
            "delay_reason": delay_reason
        }
