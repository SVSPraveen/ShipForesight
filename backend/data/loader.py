import duckdb
import os
from backend.config import get_settings

def check_tables_exist(conn) -> bool:
    """
    Checks if all required tables exist and contain data.
    """
    try:
        vendor_count = conn.execute("SELECT COUNT(*) FROM vendor_stats").fetchone()[0]
        route_count = conn.execute("SELECT COUNT(*) FROM route_stats").fetchone()[0]
        country_count = conn.execute("SELECT COUNT(*) FROM country_risk").fetchone()[0]
        holiday_count = conn.execute("SELECT COUNT(*) FROM holiday_calendar").fetchone()[0]
        lane_count = conn.execute("SELECT COUNT(*) FROM trade_lanes").fetchone()[0]
        # Also check if predictions table exists (we don't check count>0 because it starts empty)
        conn.execute("SELECT 1 FROM predictions LIMIT 1")
        return vendor_count > 0 and route_count > 0 and country_count > 0 and holiday_count > 0 and lane_count > 0
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

    # Create country_risk table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS country_risk (
        country_code VARCHAR PRIMARY KEY,
        lpi_score DOUBLE NOT NULL CHECK (lpi_score >= 1.0 AND lpi_score <= 5.0),
        customs_tier INTEGER NOT NULL CHECK (customs_tier >= 1 AND customs_tier <= 4),
        geopolitical_risk DOUBLE NOT NULL CHECK (geopolitical_risk >= 0.0 AND geopolitical_risk <= 1.0),
        port_congestion DOUBLE NOT NULL CHECK (port_congestion >= 0.0)
    );
    """)

    # Create holiday_calendar table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS holiday_calendar (
        country_code VARCHAR NOT NULL,
        holiday_date DATE NOT NULL,
        holiday_name VARCHAR NOT NULL,
        risk_weight DOUBLE NOT NULL CHECK (risk_weight >= 0.0 AND risk_weight <= 1.0),
        PRIMARY KEY (country_code, holiday_date)
    );
    """)

    # Create trade_lanes table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS trade_lanes (
        origin_country VARCHAR NOT NULL,
        destination_country VARCHAR NOT NULL,
        avg_customs_days DOUBLE NOT NULL CHECK (avg_customs_days >= 0.0),
        lane_type VARCHAR NOT NULL,
        confidence DOUBLE NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
        PRIMARY KEY (origin_country, destination_country)
    );
    """)

    # Create predictions logging table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        shipment_id VARCHAR NOT NULL,
        delay_predicted BOOLEAN NOT NULL,
        delay_probability DOUBLE NOT NULL,
        estimated_delay_days DOUBLE NOT NULL,
        delay_reason VARCHAR,
        vendor_tier VARCHAR,
        prediction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Create weather_historical table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS weather_historical (
        origin_city VARCHAR NOT NULL,
        departure_date VARCHAR NOT NULL,
        precipitation_mm DOUBLE,
        windspeed_max_kmh DOUBLE,
        snowfall_cm DOUBLE,
        weather_risk_score DOUBLE NOT NULL,
        PRIMARY KEY (origin_city, departure_date)
    );
    """)

    # Load CSV data directly using DuckDB's fast read_csv_auto
    # Also added safe fallbacks if files are not present
    tables_to_load = [
        ("vendor_stats.csv", "vendor_stats"),
        ("route_stats.csv", "route_stats"),
        ("country_risk.csv", "country_risk"),
        ("holiday_calendar.csv", "holiday_calendar"),
        ("trade_lanes.csv", "trade_lanes"),
        ("weather_historical.csv", "weather_historical")
    ]

    for csv_file, table_name in tables_to_load:
        csv_path = os.path.join("data", "raw", csv_file)
        if os.path.exists(csv_path):
            try:
                conn.execute(f"INSERT OR IGNORE INTO {table_name} SELECT * FROM read_csv_auto('{csv_path}')")
                print(f"Loaded {csv_path} into {table_name}.")
            except Exception as e:
                print(f"Failed to load {csv_path} into {table_name}: {e}")
        else:
            print(f"Warning: {csv_path} not found. Table {table_name} will be empty or rely on defaults.")

    conn.close()
    print("Feature store seed complete.")

if __name__ == "__main__":
    seed_feature_store()
