import duckdb
from backend.config import get_settings

class FeatureStore:
    def __init__(self):
        settings = get_settings()
        # Connect to the DuckDB file specified in settings
        self.conn = duckdb.connect(settings.duckdb_path)
        
        # In-memory caches for fast lookups
        self._vendor_cache = {}
        self._route_cache = {}
        
        self._load_caches()
        
    def _load_caches(self):
        """Loads vendor and route tables entirely into memory."""
        try:
            vendors = self.conn.execute("SELECT vendor_name, on_time_rate, avg_delay_days, total_shipments FROM vendor_stats").fetchall()
            for v in vendors:
                self._vendor_cache[v[0]] = {
                    "on_time_rate": v[1],
                    "avg_delay_days": v[2],
                    "total_shipments": v[3]
                }
        except Exception:
            pass
            
        try:
            routes = self.conn.execute("SELECT origin, destination, avg_delay_days, historical_count FROM route_stats").fetchall()
            for r in routes:
                key = (r[0], r[1])
                self._route_cache[key] = {
                    "avg_delay_days": r[2],
                    "historical_count": r[3]
                }
        except Exception:
            pass

    def get_vendor_stats(self, vendor_name: str) -> dict:
        """
        Retrieves vendor stats from the in-memory cache.
        Returns defaults if the vendor is not found.
        """
        if vendor_name in self._vendor_cache:
            return self._vendor_cache[vendor_name]
        
        # Defaults from spec
        return {
            "on_time_rate": 0.5,
            "avg_delay_days": 2.0,
            "total_shipments": 0
        }

    def get_route_stats(self, origin: str, destination: str) -> dict:
        """
        Retrieves route stats from the in-memory cache.
        Returns defaults if the route pair is not found.
        """
        key = (origin, destination)
        if key in self._route_cache:
            return self._route_cache[key]
            
        # Defaults from spec
        return {
            "avg_delay_days": 2.0,
            "historical_count": 0
        }

    def log_prediction(self, shipment_id: str, delay_predicted: bool, delay_probability: float, estimated_delay_days: float, delay_reason: str, vendor_tier: str):
        """Logs a prediction to the DuckDB predictions table."""
        try:
            query = """
                INSERT INTO predictions (shipment_id, delay_predicted, delay_probability, estimated_delay_days, delay_reason, vendor_tier)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            self.conn.execute(query, [shipment_id, delay_predicted, delay_probability, estimated_delay_days, delay_reason, vendor_tier])
        except Exception as e:
            print(f"Error logging prediction: {e}")

    def close(self):
        """Closes the DuckDB connection explicitly."""
        try:
            self.conn.close()
        except Exception:
            pass

    def __del__(self):
        self.close()
