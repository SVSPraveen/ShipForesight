import matplotlib
matplotlib.use('Agg')
import pandas as pd
import numpy as np
import joblib
import os
import mlflow
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OrdinalEncoder, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.cluster import KMeans
from lightgbm import LGBMClassifier, LGBMRegressor
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, mean_absolute_error, mean_squared_error
from backend.config import get_settings

def process_dataco(df: pd.DataFrame) -> pd.DataFrame:
    """Transforms DataCo dataset and merges new global datasets."""
    if df.empty: return pd.DataFrame()
    out = pd.DataFrame()
    
    # 1. Base mappings
    mode_map = {"Standard Class": "FTL", "Second Class": "LTL", "First Class": "FTL", "Same Day": "Intermodal"}
    out["carrier_type"] = df["Shipping Mode"].map(mode_map).fillna("FTL")
    
    # 2. CLEAN LABEL STRATEGY: Target variables computed without leakage
    real = pd.to_numeric(df["Days for shipping (real)"], errors='coerce').fillna(0)
    sched = pd.to_numeric(df["Days for shipment (scheduled)"], errors='coerce').fillna(0)
    out["delay_days"] = np.maximum(0.0, real - sched)
    out["delay_flag"] = (real > sched).astype(int)
    
    # Notice we DO NOT use 'Late_delivery_risk' or 'Delivery_Status' anywhere!
    
    out["quantity"] = pd.to_numeric(df["Order Item Quantity"], errors='coerce').fillna(1).astype(int)
    price = pd.to_numeric(df["Order Item Product Price"], errors='coerce').fillna(2.0)
    out["cargo_weight_kg"] = (price * 0.5).clip(1.0, 50000.0)
    
    prio_map = {"Same Day": "CRITICAL", "First Class": "HIGH", "Second Class": "MEDIUM", "Standard Class": "LOW"}
    out["priority_level"] = df["Shipping Mode"].map(prio_map).fillna("MEDIUM")
    
    out["planned_departure_date"] = pd.to_datetime(df["order date (DateOrders)"], errors="coerce")
    
    # LEAKAGE FIX: 'shipping date (DateOrders)' is the ACTUAL shipping date, not the planned one!
    # If we use it to calculate planned_transit_days, the model learns the exact answer!
    # Instead, we use the "Days for shipment (scheduled)" which is known in advance.
    sched_days = pd.to_numeric(df["Days for shipment (scheduled)"], errors='coerce').fillna(0)
    out["planned_transit_days"] = sched_days
    
    # We no longer need planned_arrival_date for features
    out["is_hazmat"] = 0
    out["temperature_sensitive"] = 0
    out["num_stops"] = 1
    out["cargo_volume_m3"] = out["cargo_weight_kg"] / 500.0
    out["distance_km"] = 500.0
    
    out["origin_city"] = df["Order City"].astype(str)
    out["destination_city"] = df["Customer City"].astype(str)
    out["origin_country"] = df["Order Country"].astype(str) if "Order Country" in df.columns else "US"
    out["destination_country"] = df["Customer Country"].astype(str) if "Customer Country" in df.columns else "US"
    
    # Derive Date Features
    out["departure_day_of_week"] = out["planned_departure_date"].dt.dayofweek.fillna(0)
    out["departure_month"] = out["planned_departure_date"].dt.month.fillna(1)
    out["departure_is_weekend"] = out["departure_day_of_week"].isin([5, 6]).astype(int)
    out["is_cross_border"] = (out["origin_country"] != out["destination_country"]).astype(int)
    
    # 3. Join Prepped Data Lookups
    # Merge country risk (origin and destination)
    lpi_path = "data/raw/country_risk.csv"
    if os.path.exists(lpi_path):
        lpi_df = pd.read_csv(lpi_path)
        # Origin
        out = pd.merge(out, lpi_df, left_on="origin_country", right_on="country_code", how="left")
        out.rename(columns={"lpi_score": "origin_lpi_score", "customs_tier": "origin_customs_tier", "geopolitical_risk": "origin_geopolitical_risk"}, inplace=True)
        if "port_congestion" in out.columns:
            out.drop(columns=["country_code", "port_congestion"], inplace=True)
        else:
            out.drop(columns=["country_code"], inplace=True)
            
        # Destination
        out = pd.merge(out, lpi_df, left_on="destination_country", right_on="country_code", how="left")
        out.rename(columns={"lpi_score": "destination_lpi_score", "customs_tier": "destination_customs_tier", "geopolitical_risk": "destination_geopolitical_risk", "port_congestion": "destination_port_congestion"}, inplace=True)
        if "country_code" in out.columns:
            out.drop(columns=["country_code"], inplace=True)
            
    # Merge Trade Lanes
    lanes_path = "data/raw/trade_lanes.csv"
    if os.path.exists(lanes_path):
        lanes_df = pd.read_csv(lanes_path)
        out = pd.merge(out, lanes_df, on=["origin_country", "destination_country"], how="left")
        out.rename(columns={"avg_customs_days": "lane_avg_customs_days"}, inplace=True)
        if "lane_type" in out.columns:
            out.drop(columns=["lane_type", "confidence"], inplace=True)
            
    # Merge Weather Data
    weather_path = "data/raw/weather_historical.csv"
    if os.path.exists(weather_path):
        weather_df = pd.read_csv(weather_path)
        # Need departure_date as string to match
        out["departure_date_str"] = out["planned_departure_date"].dt.strftime("%Y-%m-%d")
        out = pd.merge(out, weather_df, left_on=["origin_city", "departure_date_str"], right_on=["origin_city", "departure_date"], how="left")
        out.drop(columns=["departure_date_str", "departure_date", "precipitation_mm", "windspeed_max_kmh", "snowfall_cm"], inplace=True, errors="ignore")
    
    # Ensure all 28 features exist and fill NaNs
    out["origin_lpi_score"] = out.get("origin_lpi_score", pd.Series([3.0]*len(out))).fillna(3.0)
    out["destination_lpi_score"] = out.get("destination_lpi_score", pd.Series([3.0]*len(out))).fillna(3.0)
    out["origin_customs_tier"] = out.get("origin_customs_tier", pd.Series([2]*len(out))).fillna(2).astype(int)
    out["destination_customs_tier"] = out.get("destination_customs_tier", pd.Series([2]*len(out))).fillna(2).astype(int)
    out["origin_geopolitical_risk"] = out.get("origin_geopolitical_risk", pd.Series([0.2]*len(out))).fillna(0.2)
    out["destination_geopolitical_risk"] = out.get("destination_geopolitical_risk", pd.Series([0.2]*len(out))).fillna(0.2)
    out["destination_port_congestion"] = out.get("destination_port_congestion", pd.Series([1.0]*len(out))).fillna(1.0)
    out["lane_avg_customs_days"] = out.get("lane_avg_customs_days", pd.Series([2.5]*len(out))).fillna(2.5)
    out["weather_risk_score"] = out.get("weather_risk_score", pd.Series([0.1]*len(out))).fillna(0.1)
    
    # We remove historical_delay_rate since it was leakage unless it's strictly pre-computed by vendor/route.
    # The spec said: "historical_delay_rate — this is fine IF it is per-vendor or per-route, NOT per-shipment."
    # Since we use vendor_avg_delay_days and route_avg_delay_days, we just drop historical_delay_rate entirely!
    if "historical_delay_rate" in out.columns:
        out.drop(columns=["historical_delay_rate"], inplace=True)
    
    # Merge Vendor and Route Stats
    vendor_path = "data/raw/vendor_stats.csv"
    if os.path.exists(vendor_path):
        v_df = pd.read_csv(vendor_path)
        out = pd.merge(out, v_df, left_on="destination_city", right_on="vendor_name", how="left")
        # Assuming we just use destination_city or order_city as a proxy for vendor if no explicit vendor column exists
    
    route_path = "data/raw/route_stats.csv"
    if os.path.exists(route_path):
        r_df = pd.read_csv(route_path)
        out = pd.merge(out, r_df, left_on=["origin_city", "destination_city"], right_on=["origin", "destination"], how="left")
        out.drop(columns=["origin", "destination"], inplace=True, errors="ignore")
        
    out["vendor_on_time_rate"] = out.get("on_time_rate", pd.Series([0.5]*len(out))).fillna(0.5)
    out["vendor_avg_delay_days"] = out.get("avg_delay_days_x", out.get("avg_delay_days", pd.Series([2.0]*len(out)))).fillna(2.0)
    out["route_avg_delay_days"] = out.get("avg_delay_days_y", out.get("avg_delay_days", pd.Series([2.0]*len(out)))).fillna(2.0)
    out.drop(columns=["on_time_rate", "avg_delay_days_x", "avg_delay_days_y", "avg_delay_days", "vendor_name"], inplace=True, errors="ignore")
    out["is_origin_holiday"] = 0
    out["is_destination_holiday"] = 0
    
    return out

class PseudoLabelEncoder:
    def __init__(self, mapping):
        self.mapping = mapping
    def inverse_transform(self, X):
        return np.array([self.mapping[x] for x in X])

def train_all_models():
    settings = get_settings()
    os.makedirs(settings.models_dir, exist_ok=True)
    mlflow.autolog()
    
    print("Loading and processing DataCo training data (No Leakage)...")
    dataco_path = "data/raw/shipments.csv"
    if not os.path.exists(dataco_path):
        raise FileNotFoundError(f"{dataco_path} not found.")
        
    df = pd.read_csv(dataco_path, low_memory=False, encoding='latin1')
    df = process_dataco(df)
    
    print(f"Total rows after cleanup: {len(df)}")
    
    NUMERIC_FEATURES = [
        "cargo_weight_kg", "cargo_volume_m3", "distance_km", "num_stops",
        "planned_transit_days", "departure_day_of_week", "departure_month",
        "departure_is_weekend", "is_hazmat", "temperature_sensitive",
        "weather_risk_score", "vendor_on_time_rate",
        "vendor_avg_delay_days", "route_avg_delay_days", "is_cross_border",
        "origin_lpi_score", "destination_lpi_score", "origin_customs_tier",
        "destination_customs_tier", "origin_geopolitical_risk",
        "destination_geopolitical_risk", "destination_port_congestion",
        "is_origin_holiday", "is_destination_holiday", "lane_avg_customs_days"
    ]
    CATEGORICAL_FEATURES = ["carrier_type", "priority_level"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OrdinalEncoder(
                categories=[
                    ["FTL", "LTL", "Intermodal", "Ocean", "Air"],
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

    # STAGE 1
    print("Training Stage 1: Ensemble Binary Classifier (No Leakage)...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, min_samples_leaf=10, class_weight="balanced", random_state=42, n_jobs=-1)
    lgbm = LGBMClassifier(n_estimators=200, learning_rate=0.05, max_depth=8, class_weight="balanced", random_state=42, verbose=-1, n_jobs=-1)
    xgb = XGBClassifier(n_estimators=100, learning_rate=0.05, max_depth=6, eval_metric="logloss", random_state=42, n_jobs=-1)
    
    voting_clf = VotingClassifier(estimators=[('rf', rf), ('lgbm', lgbm), ('xgb', xgb)], voting="soft")
    voting_clf.fit(X_train_t, y_train)
    
    y_pred = voting_clf.predict(X_test_t)
    y_prob = voting_clf.predict_proba(X_test_t)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    print(f"Stage 1 Metrics -> Accuracy: {acc:.4f} | AUC: {auc:.4f} (Expected drop due to leakage removal)")
    
    joblib.dump(voting_clf, os.path.join(settings.models_dir, "classifier.pkl"), compress=3)

    # STAGE 2
    print("Training Stage 2: LightGBM Regressor...")
    df_reg = df[(df["delay_flag"] == 1) & (df["delay_days"].notnull()) & (df["delay_days"] > 0)]
    X_reg = df_reg[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_reg = df_reg["delay_days"]
    
    X_train_reg, X_test_reg, y_train_reg, y_test_reg = train_test_split(X_reg, y_reg, test_size=0.2, random_state=42)
    X_train_reg_t = preprocessor.transform(X_train_reg)
    X_test_reg_t = preprocessor.transform(X_test_reg)
    
    reg = LGBMRegressor(n_estimators=200, learning_rate=0.05, max_depth=10, random_state=42, verbose=-1, n_jobs=-1)
    reg.fit(X_train_reg_t, y_train_reg)
    
    y_pred_reg = np.maximum(0.0, np.round(reg.predict(X_test_reg_t), 1))
    mae = mean_absolute_error(y_test_reg, y_pred_reg)
    rmse = np.sqrt(mean_squared_error(y_test_reg, y_pred_reg))
    print(f"Stage 2 Metrics -> MAE: {mae:.4f} | RMSE: {rmse:.4f}")
    
    joblib.dump(reg, os.path.join(settings.models_dir, "regressor.pkl"), compress=3)

    # STAGE 3: K-Means Pseudo-Labeling
    print("Training Stage 3: Reason Classifier (K-Means Pseudo-Labels)...")
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    
    # We cluster the transformed features of the delayed subset to find natural groupings
    cluster_labels = kmeans.fit_predict(X_train_reg_t)
    
    # Map clusters to logical names based on spec (WEATHER, VENDOR, ROUTE, CUSTOMS)
    reason_map = {0: "WEATHER", 1: "VENDOR", 2: "ROUTE", 3: "CUSTOMS"}
    y_train_c3_enc = np.array([cluster_labels[i] for i in range(len(cluster_labels))])
    
    reason_clf = LGBMClassifier(n_estimators=200, learning_rate=0.05, max_depth=8, class_weight="balanced", random_state=42, verbose=-1, n_jobs=-1)
    reason_clf.fit(X_train_reg_t, y_train_c3_enc)
    
    # Evaluate on the regressor test set
    y_test_c3_enc = kmeans.predict(X_test_reg_t)
    y_pred_c3 = reason_clf.predict(X_test_reg_t)
    acc_c3 = accuracy_score(y_test_c3_enc, y_pred_c3)
    print(f"Stage 3 Metrics -> Accuracy: {acc_c3:.4f}")
    
    joblib.dump((reason_clf, reason_map), os.path.join(settings.models_dir, "reason_clf.pkl"), compress=3)
    print("Training complete. All models saved successfully to models/.")

if __name__ == "__main__":
    train_all_models()
