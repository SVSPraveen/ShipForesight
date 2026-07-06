import pandas as pd
from datetime import date
from typing import Dict, Any

class FeatureBuilder:
    @staticmethod
    @staticmethod
    def build(request_dict: Dict[str, Any], vendor_dict: Dict[str, Any], route_dict: Dict[str, Any], origin_risk_dict: Dict[str, Any], dest_risk_dict: Dict[str, Any], lane_dict: Dict[str, Any], is_origin_holiday: int, is_dest_holiday: int) -> pd.DataFrame:
        # Extract dates safely
        dep_date = request_dict.get("planned_departure_date")
        
        # Derived dates
        # LEAKAGE FIX: Do NOT compute transit days from arrival - departure (arrival date is actual delivery in historical data).
        # We must use the scheduled transit days which is inferred from the priority level, or provided by the request.
        # If the frontend passes "scheduled_transit_days", use it. Otherwise, default to 2.
        planned_transit_days = request_dict.get("scheduled_transit_days", 2)
        
        departure_day_of_week = dep_date.dayofweek if (dep_date and hasattr(dep_date, 'dayofweek')) else (dep_date.weekday() if dep_date else 0)
        departure_month = dep_date.month if dep_date else 1
        departure_is_weekend = 1 if departure_day_of_week in (5, 6) else 0

        is_hazmat = int(request_dict.get("is_hazmat", False))
        temperature_sensitive = int(request_dict.get("temperature_sensitive", False))

        # Raw floats/ints
        cargo_weight_kg = float(request_dict.get("cargo_weight_kg", 1.0))
        cargo_volume_m3 = float(request_dict.get("cargo_volume_m3", 1.0))
        distance_km = float(request_dict.get("distance_km", 1.0))
        num_stops = int(request_dict.get("num_stops", 0))
        weather_risk_score = float(request_dict.get("weather_risk_score", 0.1))
        
        # Enrichment lookups
        vendor_on_time_rate = float(vendor_dict.get("on_time_rate", 0.5))
        vendor_avg_delay_days = float(vendor_dict.get("avg_delay_days", 2.0))
        route_avg_delay_days = float(route_dict.get("avg_delay_days", 2.0))
        
        # New Global Features
        origin_country = request_dict.get("origin_country", "US")
        destination_country = request_dict.get("destination_country", "US")
        is_cross_border = 1 if origin_country != destination_country else 0
        
        origin_lpi_score = float(origin_risk_dict.get("lpi_score", 3.0))
        destination_lpi_score = float(dest_risk_dict.get("lpi_score", 3.0))
        origin_customs_tier = int(origin_risk_dict.get("customs_tier", 2))
        destination_customs_tier = int(dest_risk_dict.get("customs_tier", 2))
        origin_geopolitical_risk = float(origin_risk_dict.get("geopolitical_risk", 0.2))
        destination_geopolitical_risk = float(dest_risk_dict.get("geopolitical_risk", 0.2))
        destination_port_congestion = float(dest_risk_dict.get("port_congestion", 1.0))
        
        lane_avg_customs_days = float(lane_dict.get("avg_customs_days", 2.5))

        # Categorical strings
        carrier_type = str(request_dict.get("carrier_type", "FTL"))
        priority_level = str(request_dict.get("priority_level", "MEDIUM"))

        features = {
            "cargo_weight_kg": cargo_weight_kg,
            "cargo_volume_m3": cargo_volume_m3,
            "distance_km": distance_km,
            "num_stops": num_stops,
            "planned_transit_days": planned_transit_days,
            "departure_day_of_week": departure_day_of_week,
            "departure_month": departure_month,
            "departure_is_weekend": departure_is_weekend,
            "is_hazmat": is_hazmat,
            "temperature_sensitive": temperature_sensitive,
            "carrier_type": carrier_type,
            "priority_level": priority_level,
            "weather_risk_score": weather_risk_score,
            "vendor_on_time_rate": vendor_on_time_rate,
            "vendor_avg_delay_days": vendor_avg_delay_days,
            "route_avg_delay_days": route_avg_delay_days,
            "is_cross_border": is_cross_border,
            "origin_lpi_score": origin_lpi_score,
            "destination_lpi_score": destination_lpi_score,
            "origin_customs_tier": origin_customs_tier,
            "destination_customs_tier": destination_customs_tier,
            "origin_geopolitical_risk": origin_geopolitical_risk,
            "destination_geopolitical_risk": destination_geopolitical_risk,
            "destination_port_congestion": destination_port_congestion,
            "is_origin_holiday": is_origin_holiday,
            "is_destination_holiday": is_dest_holiday,
            "lane_avg_customs_days": lane_avg_customs_days
        }

        # Convert to DataFrame
        df = pd.DataFrame([features])
        
        # Absolute safety net: explicitly fill any lingering NaNs with 0.0
        df.fillna(0.0, inplace=True)
        
        return df
