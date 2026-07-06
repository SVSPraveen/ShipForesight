import pandas as pd
import numpy as np
import joblib
import os
import mlflow
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OrdinalEncoder, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from lightgbm import LGBMClassifier, LGBMRegressor
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, mean_absolute_error, mean_squared_error
from backend.config import get_settings

def assign_delay_reason(row):
    """Rule-based assignment for delay reason matching Appendix C."""
    if row["weather_risk_score"] >= 0.6:
        return "WEATHER"
    elif row["vendor_on_time_rate"] < 0.55:
        return "VENDOR"
    elif row["route_avg_delay_days"] >= 2.5:
        return "ROUTE"
    else:
        return "CUSTOM"

def process_dataco(df: pd.DataFrame) -> pd.DataFrame:
    """Transforms DataCo dataset exactly as specified in Appendix C."""
    if df.empty: return pd.DataFrame()
    out = pd.DataFrame()
    
    mode_map = {"Standard Class": "FTL", "Second Class": "LTL", "First Class": "FTL", "Same Day": "Intermodal"}
    out["carrier_type"] = df["Shipping Mode"].map(mode_map).fillna("FTL")
    
    out["delay_flag"] = df["Late_delivery_risk"].fillna(0).astype(int)
    
    real = pd.to_numeric(df["Days for shipping (real)"], errors='coerce').fillna(0)
    sched = pd.to_numeric(df["Days for shipment (scheduled)"], errors='coerce').fillna(0)
    out["delay_days"] = np.maximum(0.0, real - sched)
    
    out["quantity"] = pd.to_numeric(df["Order Item Quantity"], errors='coerce').fillna(1).astype(int)
    
    price = pd.to_numeric(df["Order Item Product Price"], errors='coerce').fillna(2.0)
    out["cargo_weight_kg"] = (price * 0.5).clip(1.0, 50000.0)
    
    prio_map = {"Same Day": "CRITICAL", "First Class": "HIGH", "Second Class": "MEDIUM", "Standard Class": "LOW"}
    out["priority_level"] = df["Shipping Mode"].map(prio_map).fillna("MEDIUM")
    
    out["planned_departure_date"] = pd.to_datetime(df["order date (DateOrders)"], errors="coerce")
    out["planned_arrival_date"] = pd.to_datetime(df["shipping date (DateOrders)"], errors="coerce")
    
    out["is_hazmat"] = 0
    out["temperature_sensitive"] = 0
    out["num_stops"] = 1
    out["cargo_volume_m3"] = out["cargo_weight_kg"] / 500.0
    out["distance_km"] = 500.0
    
    out["origin_city"] = df["Order City"].astype(str)
    out["destination_city"] = df["Customer City"].astype(str)
    
    # historical delay rate per origin/destination
    out["historical_delay_rate"] = out.groupby(["origin_city", "destination_city"])["delay_flag"].transform("mean")
    
    return out

def train_all_models():
    settings = get_settings()
    os.makedirs(settings.models_dir, exist_ok=True)
    
    # 1. Start MLflow Autologging
    mlflow.autolog()
    
    print("Loading and processing DataCo training data...")
    dataco_path = "data/raw/shipments.csv"
    if not os.path.exists(dataco_path):
        raise FileNotFoundError(f"{dataco_path} not found. Please download the training data.")
        
    df = pd.read_csv(dataco_path, low_memory=False)
    df = process_dataco(df)
    
    # Applying drop rules from spec
    df = df.dropna(subset=["planned_departure_date", "planned_arrival_date"])
    df = df[df["planned_arrival_date"] > df["planned_departure_date"]]
    df = df[df["cargo_weight_kg"] > 0]
    
    # Derived date features
    df["planned_transit_days"] = (df["planned_arrival_date"] - df["planned_departure_date"]).dt.days
    df["departure_day_of_week"] = df["planned_departure_date"].dt.isoweekday()
    df["departure_month"] = df["planned_departure_date"].dt.month
    df["departure_is_weekend"] = df["departure_day_of_week"].isin([6, 7]).astype(int)
    
    # Assign defaults for vendor and route
    df["vendor_on_time_rate"] = 0.5
    df["vendor_avg_delay_days"] = 2.0
    df["route_avg_delay_days"] = 2.0
    df["weather_risk_score"] = 0.2
    
    # Assign delay reason
    df["delay_reason"] = "NONE"
    mask = df["delay_flag"] == 1
    df.loc[mask, "delay_reason"] = df[mask].apply(assign_delay_reason, axis=1)

    print(f"Total rows after cleanup: {len(df)}")
    
    NUMERIC_FEATURES = [
        "cargo_weight_kg", "cargo_volume_m3", "distance_km", "num_stops",
        "weather_risk_score", "historical_delay_rate", "planned_transit_days",
        "vendor_on_time_rate", "vendor_avg_delay_days", "route_avg_delay_days",
        "departure_day_of_week", "departure_month", "departure_is_weekend",
        "is_hazmat", "temperature_sensitive"
    ]
    CATEGORICAL_FEATURES = ["carrier_type", "priority_level"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OrdinalEncoder(
                categories=[
                    ["FTL", "LTL", "Intermodal"],
                    ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
                ],
                handle_unknown="use_encoded_value",
                unknown_value=-1
            ), CATEGORICAL_FEATURES)
        ],
        remainder="drop"
    )

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_clf = df["delay_flag"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y_clf, test_size=0.2, random_state=42, stratify=y_clf)
    
    print("Fitting preprocessor...")
    X_train_t = preprocessor.fit_transform(X_train)
    X_test_t = preprocessor.transform(X_test)
    joblib.dump(preprocessor, os.path.join(settings.models_dir, "preprocessor.pkl"), compress=3)

    # ---------------------------------------------------------
    # STAGE 1: Ensemble Binary Classifier
    # ---------------------------------------------------------
    print("Training Stage 1: Ensemble Binary Classifier...")
    rf = RandomForestClassifier(n_estimators=300, max_depth=12, min_samples_leaf=5, class_weight="balanced", random_state=42, n_jobs=-1)
    lgbm = LGBMClassifier(n_estimators=400, learning_rate=0.05, max_depth=8, num_leaves=63, subsample=0.8, colsample_bytree=0.8, class_weight="balanced", random_state=42, verbose=-1, n_jobs=-1)
    xgb = XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=0.8, eval_metric="logloss", random_state=42, n_jobs=-1)
    
    voting_clf = VotingClassifier(estimators=[('rf', rf), ('lgbm', lgbm), ('xgb', xgb)], voting="soft")
    voting_clf.fit(X_train_t, y_train)
    
    y_pred = voting_clf.predict(X_test_t)
    y_prob = voting_clf.predict_proba(X_test_t)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    print(f"Stage 1 Metrics -> Accuracy: {acc:.4f} | AUC: {auc:.4f}")
    
    joblib.dump(voting_clf, os.path.join(settings.models_dir, "classifier.pkl"), compress=3)

    # ---------------------------------------------------------
    # STAGE 2: LightGBM Regressor
    # ---------------------------------------------------------
    print("Training Stage 2: LightGBM Regressor...")
    df_reg = df[(df["delay_flag"] == 1) & (df["delay_days"].notnull()) & (df["delay_days"] > 0)]
    X_reg = df_reg[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_reg = df_reg["delay_days"]
    
    X_train_reg, X_test_reg, y_train_reg, y_test_reg = train_test_split(X_reg, y_reg, test_size=0.2, random_state=42)
    X_train_reg_t = preprocessor.transform(X_train_reg)
    X_test_reg_t = preprocessor.transform(X_test_reg)
    
    reg = LGBMRegressor(n_estimators=500, learning_rate=0.03, max_depth=10, num_leaves=127, subsample=0.8, colsample_bytree=0.8, min_child_samples=20, reg_alpha=0.1, reg_lambda=0.1, random_state=42, verbose=-1, n_jobs=-1)
    reg.fit(X_train_reg_t, y_train_reg)
    
    y_pred_reg = np.maximum(0.0, np.round(reg.predict(X_test_reg_t), 1))
    mae = mean_absolute_error(y_test_reg, y_pred_reg)
    rmse = np.sqrt(mean_squared_error(y_test_reg, y_pred_reg))
    print(f"Stage 2 Metrics -> MAE: {mae:.4f} | RMSE: {rmse:.4f}")
    
    joblib.dump(reg, os.path.join(settings.models_dir, "regressor.pkl"), compress=3)

    # ---------------------------------------------------------
    # STAGE 3: Multi-Class Reason Classifier
    # ---------------------------------------------------------
    print("Training Stage 3: Reason Classifier...")
    df_clf3 = df[(df["delay_flag"] == 1) & (df["delay_reason"].notnull()) & (df["delay_reason"] != "NONE")]
    X_clf3 = df_clf3[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_clf3 = df_clf3["delay_reason"]
    
    le = LabelEncoder()
    y_clf3_enc = le.fit_transform(y_clf3)
    
    X_train_c3, X_test_c3, y_train_c3, y_test_c3 = train_test_split(X_clf3, y_clf3_enc, test_size=0.2, random_state=42, stratify=y_clf3_enc)
    X_train_c3_t = preprocessor.transform(X_train_c3)
    X_test_c3_t = preprocessor.transform(X_test_c3)
    
    reason_clf = LGBMClassifier(n_estimators=400, learning_rate=0.05, max_depth=8, num_leaves=63, subsample=0.8, colsample_bytree=0.8, class_weight="balanced", random_state=42, verbose=-1, n_jobs=-1)
    reason_clf.fit(X_train_c3_t, y_train_c3)
    
    y_pred_c3 = reason_clf.predict(X_test_c3_t)
    acc_c3 = accuracy_score(y_test_c3, y_pred_c3)
    print(f"Stage 3 Metrics -> Accuracy: {acc_c3:.4f}")
    
    # Save model and label encoder as a tuple
    joblib.dump((reason_clf, le), os.path.join(settings.models_dir, "reason_clf.pkl"), compress=3)
    print("Training complete. All models saved successfully to models/.")

if __name__ == "__main__":
    train_all_models()
