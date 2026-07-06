"""
fetch_weather.py
────────────────
Fetches historical weather data from Open-Meteo (completely free, no API key)
for every unique city + date pair found in data/raw/shipments.csv.

Outputs: data/raw/weather_historical.csv

Columns produced:
  - origin_city
  - departure_date       (YYYY-MM-DD)
  - precipitation_mm     (total daily precipitation)
  - windspeed_max_kmh    (max 10m wind speed)
  - snowfall_cm          (daily snowfall)
  - weather_risk_score   (0.0 – 1.0, derived from above three signals)

Usage:
    python scripts/fetch_weather.py

Requirements (already in venv):
    requests, pandas
"""

import os
import time
import json
import requests
import pandas as pd
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────
SHIPMENTS_CSV   = "data/raw/shipments.csv"
OUTPUT_CSV      = "data/raw/weather_historical.csv"
GEOCODE_CACHE   = "data/raw/geocode_cache.json"   # avoids re-geocoding same city
REQUEST_DELAY   = 0.25   # seconds between API calls (stay well under free limit)

# Open-Meteo endpoints (no auth needed)
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"

# ── Helpers ──────────────────────────────────────────────────────────────────
def geocode(city: str, country: str, cache: dict):
    """Returns (lat, lon) for a city, using a local cache to avoid repeat lookups."""
    key = f"{city}|{country}"
    if key in cache:
        return cache[key]

    try:
        r = requests.get(GEOCODE_URL, params={"name": city, "count": 1, "language": "en"}, timeout=10)
        r.raise_for_status()
        results = r.json().get("results", [])
        if results:
            lat, lon = results[0]["latitude"], results[0]["longitude"]
            cache[key] = (lat, lon)
            return (lat, lon)
    except Exception as e:
        print(f"  [GEOCODE ERROR] {city}, {country}: {e}")
    cache[key] = None
    return None


def fetch_weather(lat: float, lon: float, date_str: str) -> dict:
    """
    Fetches daily weather from Open-Meteo historical archive for a single date.
    Returns dict with precipitation_mm, windspeed_max_kmh, snowfall_cm.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date_str,
        "end_date": date_str,
        "daily": "precipitation_sum,windspeed_10m_max,snowfall_sum",
        "timezone": "auto",
    }
    try:
        r = requests.get(WEATHER_URL, params=params, timeout=15)
        r.raise_for_status()
        daily = r.json().get("daily", {})
        precip   = (daily.get("precipitation_sum") or [0.0])[0] or 0.0
        wind     = (daily.get("windspeed_10m_max")  or [0.0])[0] or 0.0
        snowfall = (daily.get("snowfall_sum")        or [0.0])[0] or 0.0
        return {"precipitation_mm": precip, "windspeed_max_kmh": wind, "snowfall_cm": snowfall}
    except Exception as e:
        print(f"  [WEATHER ERROR] lat={lat} lon={lon} date={date_str}: {e}")
        return {"precipitation_mm": 0.0, "windspeed_max_kmh": 0.0, "snowfall_cm": 0.0}


def compute_risk_score(precip: float, wind: float, snowfall: float) -> float:
    """
    Converts raw weather readings into a 0-1 risk score.

    Thresholds (tuned to logistics disruption research):
      - Precipitation >= 30mm/day  ->  severe (hurricane / monsoon level)
      - Wind >= 70 km/h            ->  severe gale
      - Snowfall >= 10 cm/day      ->  moderate disruption

    Risk = clamped weighted sum of individual scores.
    """
    p_score = min(precip   / 30.0,  1.0) * 0.50  # weight: 50%
    w_score = min(wind     / 70.0,  1.0) * 0.35  # weight: 35%
    s_score = min(snowfall / 10.0,  1.0) * 0.15  # weight: 15%
    return round(min(p_score + w_score + s_score, 1.0), 4)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("ShipForesight -- Open-Meteo Historical Weather Fetcher")
    print("=" * 60)

    # Load geocode cache
    geocode_cache = {}
    if os.path.exists(GEOCODE_CACHE):
        with open(GEOCODE_CACHE, "r") as f:
            raw = json.load(f)
            geocode_cache = {k: tuple(v) if v else None for k, v in raw.items()}
    print(f"Loaded {len(geocode_cache)} cached geocodes from {GEOCODE_CACHE}")

    # If output already exists, load done keys so we skip already-fetched rows
    done_keys = set()
    if os.path.exists(OUTPUT_CSV):
        existing = pd.read_csv(OUTPUT_CSV, usecols=["origin_city", "departure_date"])
        done_keys = set(zip(existing["origin_city"], existing["departure_date"]))
        print(f"Resuming -- {len(done_keys)} city/date pairs already fetched.")

    # Load shipments and extract unique city + date pairs
    print(f"\nReading {SHIPMENTS_CSV} ...")
    df = pd.read_csv(SHIPMENTS_CSV, low_memory=False, encoding="latin1",
                     usecols=["Order City", "Order Country", "order date (DateOrders)"])

    df["parsed_date"] = pd.to_datetime(df["order date (DateOrders)"], errors="coerce")
    df = df.dropna(subset=["parsed_date"])
    df["departure_date"] = df["parsed_date"].dt.strftime("%Y-%m-%d")

    pairs = (
        df[["Order City", "Order Country", "departure_date"]]
        .drop_duplicates()
        .rename(columns={"Order City": "city", "Order Country": "country"})
        .reset_index(drop=True)
    )

    # Filter to only dates Open-Meteo supports (goes back to 1940)
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    pairs = pairs[pairs["departure_date"] <= today_str]

    # Remove already-fetched pairs
    pairs = pairs[~pairs.apply(lambda r: (r["city"], r["departure_date"]) in done_keys, axis=1)]

    # Group by city and find the min and max date needed
    city_dates = pairs.groupby(["city", "country"]).agg(
        start_date=("departure_date", "min"),
        end_date=("departure_date", "max")
    ).reset_index()

    total = len(city_dates)
    print(f"Unique cities to fetch: {total} (bulk fetching date ranges!)\n")

    if total == 0:
        print("Nothing new to fetch. Output is already up-to-date!")
        return

    rows = []
    errors = 0

    for i, (_, row) in enumerate(city_dates.iterrows(), 1):
        city    = row["city"]
        country = row["country"]
        start   = row["start_date"]
        end     = row["end_date"]

        if i % 100 == 0 or i == 1:
            print(f"  [{i}/{total}] Bulk fetching {city}, {country} ({start} to {end}) ...")

        coords = geocode(city, country, geocode_cache)
        if coords is None:
            # City not found -- skip, trainer will use defaults
            errors += 1
        else:
            lat, lon = coords
            # Fetch the entire date range in ONE call
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": start,
                "end_date": end,
                "daily": "precipitation_sum,windspeed_10m_max,snowfall_sum",
                "timezone": "auto",
            }
            try:
                r = requests.get(WEATHER_URL, params=params, timeout=15)
                r.raise_for_status()
                daily = r.json().get("daily", {})
                dates = daily.get("time", [])
                precips = daily.get("precipitation_sum", [])
                winds = daily.get("windspeed_10m_max", [])
                snows = daily.get("snowfall_sum", [])
                
                for j in range(len(dates)):
                    p = precips[j] if precips[j] is not None else 0.0
                    w = winds[j] if winds[j] is not None else 0.0
                    s = snows[j] if snows[j] is not None else 0.0
                    rows.append({
                        "origin_city": city,
                        "departure_date": dates[j],
                        "precipitation_mm": p,
                        "windspeed_max_kmh": w,
                        "snowfall_cm": s,
                        "weather_risk_score": compute_risk_score(p, w, s)
                    })
            except Exception as e:
                pass

        time.sleep(REQUEST_DELAY)

        # Flush every 20 cities
        if i % 20 == 0:
            _flush(rows, OUTPUT_CSV)
            rows = []

    # Final flush
    if rows:
        _flush(rows, OUTPUT_CSV)

    # Save geocode cache
    with open(GEOCODE_CACHE, "w") as f:
        json.dump({k: list(v) if v else None for k, v in geocode_cache.items()}, f)

    print(f"\nDone! Weather data saved to: {OUTPUT_CSV}")
    print(f"   Geocode failures: {errors}/{total}")


def _flush(rows: list, path: str):
    """Appends a batch of rows to the output CSV."""
    batch = pd.DataFrame(rows)[
        ["origin_city", "departure_date", "precipitation_mm",
         "windspeed_max_kmh", "snowfall_cm", "weather_risk_score"]
    ]
    write_header = not os.path.exists(path)
    batch.to_csv(path, mode="a", header=write_header, index=False)
    print(f"  -> Flushed {len(rows)} rows to {path}")


if __name__ == "__main__":
    main()
