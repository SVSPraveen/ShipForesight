import duckdb
from backend.config import get_settings

class FeatureStore:
    def __init__(self):
        settings = get_settings()
        # Connect to the DuckDB file specified in settings
        self.conn = duckdb.connect(settings.duckdb_path)

    def get_vendor_stats(self, vendor_name: str) -> dict:
        """
        Queries vendor_stats by vendor_name using parameterized SQL.
        Returns defaults if the vendor is not found.
        """
        query = """
            SELECT on_time_rate, avg_delay_days, total_shipments
            FROM vendor_stats
            WHERE vendor_name = ?
        """
        # Parameterized query (no string formatting)
        result = self.conn.execute(query, [vendor_name]).fetchone()
        
        if result:
            return {
                "on_time_rate": result[0],
                "avg_delay_days": result[1],
                "total_shipments": result[2]
            }
        else:
            # Defaults from spec
            return {
                "on_time_rate": 0.5,
                "avg_delay_days": 2.0,
                "total_shipments": 0
            }

    def get_route_stats(self, origin: str, destination: str) -> dict:
        """
        Queries route_stats by origin and destination using parameterized SQL.
        Returns defaults if the route pair is not found.
        """
        query = """
            SELECT avg_delay_days, historical_count
            FROM route_stats
            WHERE origin = ? AND destination = ?
        """
        # Parameterized query
        result = self.conn.execute(query, [origin, destination]).fetchone()
        
        if result:
            return {
                "avg_delay_days": result[0],
                "historical_count": result[1]
            }
        else:
            # Defaults from spec
            return {
                "avg_delay_days": 2.0,
                "historical_count": 0
            }

    def close(self):
        """Closes the DuckDB connection explicitly."""
        try:
            self.conn.close()
        except Exception:
            pass

    def __del__(self):
        self.close()
