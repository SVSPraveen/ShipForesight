import pandas as pd
from datetime import date
from typing import Dict, Any

class FeatureBuilder:
    @staticmethod
    def build(request_dict: Dict[str, Any], vendor_dict: Dict[str, Any], route_dict: Dict[str, Any]) -> pd.DataFrame:
        """
        Takes a sanitized ShipmentRequest dict, vendor metrics dict, and route metrics dict.
        Returns a single-row pandas DataFrame with exactly 17 columns in the specified order.
        Never allows NaNs to be passed to the model.
        """
        # Extract dates safely
        dep_date = request_dict.get("planned_departure_date")
        arr_date = request_dict.get("planned_arrival_date")
        
        # Compute derived date features
        planned_transit_days = (arr_date - dep_date).days if arr_date and dep_date else 1
        departure_day_of_week = dep_date.isoweekday() if dep_date else 1
        departure_month = dep_date.month if dep_date else 1
        departure_is_weekend = 1 if departure_day_of_week in (6, 7) else 0

        # Convert explicit boolean fields to int (as per spec Section 3.1)
        is_hazmat = int(request_dict.get("is_hazmat", False))
        temperature_sensitive = int(request_dict.get("temperature_sensitive", False))

        # Extract numeric fields with safe fallbacks (avoiding NaN)
        cargo_weight_kg = float(request_dict.get("cargo_weight_kg", 1.0))
        cargo_volume_m3 = float(request_dict.get("cargo_volume_m3", 1.0))
        distance_km = float(request_dict.get("distance_km", 1.0))
        num_stops = int(request_dict.get("num_stops", 0))
        weather_risk_score = float(request_dict.get("weather_risk_score", 0.0))
        historical_delay_rate = float(request_dict.get("historical_delay_rate", 0.0))
        
        # Extract enriched DuckDB fields with safe defaults
        vendor_on_time_rate = float(vendor_dict.get("on_time_rate", 0.5))
        vendor_avg_delay_days = float(vendor_dict.get("avg_delay_days", 2.0))
        route_avg_delay_days = float(route_dict.get("avg_delay_days", 2.0))

        # Categorical strings
        carrier_type = str(request_dict.get("carrier_type", "FTL"))
        priority_level = str(request_dict.get("priority_level", "MEDIUM"))

        # Construct exact ordered feature dictionary matching Section 3.1
        features = {
            "cargo_weight_kg": cargo_weight_kg,
            "cargo_volume_m3": cargo_volume_m3,
            "distance_km": distance_km,
            "num_stops": num_stops,
            "weather_risk_score": weather_risk_score,
            "historical_delay_rate": historical_delay_rate,
            "planned_transit_days": planned_transit_days,
            "vendor_on_time_rate": vendor_on_time_rate,
            "vendor_avg_delay_days": vendor_avg_delay_days,
            "route_avg_delay_days": route_avg_delay_days,
            "departure_day_of_week": departure_day_of_week,
            "departure_month": departure_month,
            "departure_is_weekend": departure_is_weekend,
            "is_hazmat": is_hazmat,
            "temperature_sensitive": temperature_sensitive,
            "carrier_type": carrier_type,
            "priority_level": priority_level
        }

        # Convert to DataFrame
        df = pd.DataFrame([features])
        
        # Absolute safety net: explicitly fill any lingering NaNs with 0.0
        df.fillna(0.0, inplace=True)
        
        return df
