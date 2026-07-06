from backend.data.feature_store import FeatureStore
from datetime import date

class GlobalEnricher:
    def __init__(self, feature_store: FeatureStore):
        self.feature_store = feature_store

    def get_country_risk(self, country_code: str) -> dict:
        """Fetches country_risk metrics from DuckDB."""
        query = """
            SELECT lpi_score, customs_tier, geopolitical_risk, port_congestion
            FROM country_risk
            WHERE country_code = ?
        """
        try:
            result = self.feature_store.conn.execute(query, [country_code]).fetchone()
        except Exception:
            result = None
            
        if result:
            return {
                "lpi_score": result[0],
                "customs_tier": result[1],
                "geopolitical_risk": result[2],
                "port_congestion": result[3]
            }
        else:
            return {
                "lpi_score": 3.0,
                "customs_tier": 2,
                "geopolitical_risk": 0.2,
                "port_congestion": 1.0
            }

    def check_holiday(self, country_code: str, query_date: date) -> int:
        """Checks if a date is a holiday for the given country."""
        query = """
            SELECT 1
            FROM holiday_calendar
            WHERE country_code = ? AND holiday_date = ?
        """
        try:
            result = self.feature_store.conn.execute(query, [country_code, query_date]).fetchone()
        except Exception:
            result = None
        return 1 if result else 0

    def get_trade_lane(self, origin: str, destination: str) -> dict:
        """Fetches trade lane stats from DuckDB."""
        query = """
            SELECT avg_customs_days
            FROM trade_lanes
            WHERE origin_country = ? AND destination_country = ?
        """
        try:
            result = self.feature_store.conn.execute(query, [origin, destination]).fetchone()
        except Exception:
            result = None
            
        if result:
            return {
                "avg_customs_days": result[0]
            }
        else:
            return {
                "avg_customs_days": 2.5
            }
            
    def get_weather_risk(self, origin_city: str, departure_date: str) -> float:
        """Fetches the precomputed weather risk score from DuckDB."""
        query = """
            SELECT weather_risk_score
            FROM weather_historical
            WHERE origin_city = ? AND departure_date = ?
        """
        try:
            result = self.feature_store.conn.execute(query, [origin_city, departure_date]).fetchone()
        except Exception:
            result = None
            
        if result:
            return result[0]
        else:
            return 0.1 # safe default if no weather found
