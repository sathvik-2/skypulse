import os
import json
import pandas as pd

from pipeline.utils.config import load_config
from pipeline.utils.logger import get_logger

logger = get_logger("transform")

def clean_weather_data(raw_filepath=None, output_csv_path=None):
    """
    Transforms raw JSON weather records into a flattened, typed, and clean DataFrame/CSV.
    """
    config = load_config()
    
    if raw_filepath is None:
        raw_dir = config.get("paths", {}).get("raw_data_dir", "data/raw")
        raw_filepath = os.path.join(raw_dir, "weather_raw.json")
        
    if output_csv_path is None:
        processed_dir = config.get("paths", {}).get("processed_data_dir", "data/processed")
        output_csv_path = os.path.join(processed_dir, "weather_clean.csv")

    logger.info(f"Starting transformation: reading {raw_filepath}...")

    if not os.path.exists(raw_filepath):
        logger.error(f"Cannot transform: raw data file '{raw_filepath}' does not exist.")
        return None

    try:
        with open(raw_filepath, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read or parse JSON file {raw_filepath}: {e}")
        return None

    if not raw_data:
        logger.warning(f"Raw data file '{raw_filepath}' is empty.")
        return None

    # Flatten nested payload
    rows = []
    for item in raw_data:
        if not isinstance(item, dict):
            continue

        city = item.get("city")
        current = item.get("current", {})

        row = {
            "city": city.strip() if isinstance(city, str) else city,
            "date": current.get("time"),
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation")
        }
        rows.append(row)

    if not rows:
        logger.warning("No valid records found in raw payload.")
        return None

    df = pd.DataFrame(rows)

    # 1. Parse dates and drop rows with invalid dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    initial_count = len(df)
    df = df.dropna(subset=["city", "date"])

    # 2. Type casting & Null safety
    # Default null temperatures/precipitations to 0.0 or forward fill if needed
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce").fillna(0.0).astype(float)
    df["precipitation"] = pd.to_numeric(df["precipitation"], errors="coerce").fillna(0.0).astype(float)
    df["humidity"] = pd.to_numeric(df["humidity"], errors="coerce").fillna(0).astype(int)

    # Format date string for standard SQL DATETIME (YYYY-MM-DD HH:MM:SS)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d %H:%M:%S")

    df = df.reset_index(drop=True)

    # 3. Save to clean CSV
    try:
        os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
        df.to_csv(output_csv_path, index=False)
        logger.info(f"Transformation complete! Cleaned {len(df)} records (dropped {initial_count - len(df)} corrupt).")
        logger.info(f"Saved clean CSV to '{output_csv_path}'")
        return df
    except IOError as e:
        logger.error(f"Failed to write clean CSV to {output_csv_path}: {e}")
        return df

if __name__ == "__main__":
    df = clean_weather_data()
    if df is not None:
        print("\nCleaned Data Preview:")
        print(df)
