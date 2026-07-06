import duckdb
import os
from backend.config import get_settings

def check_tables_exist(conn) -> bool:
    """
    Checks if both vendor_stats and route_stats tables exist and contain data.
    """
    try:
        vendor_count = conn.execute("SELECT COUNT(*) FROM vendor_stats").fetchone()[0]
        route_count = conn.execute("SELECT COUNT(*) FROM route_stats").fetchone()[0]
        return vendor_count > 0 and route_count > 0
    except duckdb.CatalogException:
        # Table does not exist
        return False

def seed_feature_store():
    """
    Creates tables based on the spec and loads CSV files from data/raw/ into DuckDB.
    Skips if tables already exist and have data.
    """
    settings = get_settings()
    
    # Ensure the directory for the db exists
    os.makedirs(os.path.dirname(settings.duckdb_path), exist_ok=True)
    
    conn = duckdb.connect(settings.duckdb_path)
    
    if check_tables_exist(conn):
        print("DuckDB tables already exist and contain data. Skipping seed.")
        conn.close()
        return

    print("Creating tables and seeding data into DuckDB...")

    # Create vendor_stats table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS vendor_stats (
        vendor_name       VARCHAR NOT NULL,
        on_time_rate      DOUBLE  NOT NULL CHECK (on_time_rate >= 0.0 AND on_time_rate <= 1.0),
        avg_delay_days    DOUBLE  NOT NULL CHECK (avg_delay_days >= 0.0),
        total_shipments   INTEGER NOT NULL CHECK (total_shipments >= 0),
        PRIMARY KEY (vendor_name)
    );
    """)

    # Create route_stats table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS route_stats (
        origin            VARCHAR NOT NULL,
        destination       VARCHAR NOT NULL,
        avg_delay_days    DOUBLE  NOT NULL CHECK (avg_delay_days >= 0.0),
        historical_count  INTEGER NOT NULL CHECK (historical_count >= 0),
        PRIMARY KEY (origin, destination)
    );
    """)

    # Load CSV data directly using DuckDB's fast read_csv_auto
    vendor_csv_path = "data/raw/vendor_stats.csv"
    route_csv_path = "data/raw/route_stats.csv"

    if os.path.exists(vendor_csv_path):
        conn.execute(f"INSERT OR IGNORE INTO vendor_stats SELECT * FROM read_csv_auto('{vendor_csv_path}')")
        print(f"Loaded {vendor_csv_path} into vendor_stats.")
    else:
        print(f"Warning: {vendor_csv_path} not found. Table is empty.")

    if os.path.exists(route_csv_path):
        conn.execute(f"INSERT OR IGNORE INTO route_stats SELECT * FROM read_csv_auto('{route_csv_path}')")
        print(f"Loaded {route_csv_path} into route_stats.")
    else:
        print(f"Warning: {route_csv_path} not found. Table is empty.")

    conn.close()
    print("Feature store seed complete.")

if __name__ == "__main__":
    seed_feature_store()
