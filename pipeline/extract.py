import os
import json
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pipeline.utils.config import load_config
from pipeline.utils.logger import get_logger

logger = get_logger("extract")

def create_retry_session(retries=3, backoff_factor=1.5, status_forcelist=(429, 500, 502, 503, 504)):
    """Creates a requests Session with automated exponential backoff retries."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def fetch_weather(city_name, lat, lon, session=None, config=None):
    """Fetches real-time weather data for a single city with retries and logging."""
    if config is None:
        config = load_config()
    if session is None:
        session = create_retry_session()

    url = config.get("api", {}).get("open_meteo_url", "https://api.open-meteo.com/v1/forecast")
    metrics = config.get("api", {}).get("metrics", "temperature_2m,relative_humidity_2m,precipitation")
    timeout = config.get("api", {}).get("timeout_seconds", 10)

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": metrics
    }

    try:
        logger.info(f"Fetching weather for {city_name} (lat: {lat}, lon: {lon})...")
        response = session.get(url, params=params, timeout=timeout)

        if response.status_code == 200:
            data = response.json()
            data["city"] = city_name
            data["ingestion_timestamp"] = datetime.now().isoformat()
            logger.info(f"Successfully fetched weather for {city_name} (Status: {response.status_code})")
            return data
        else:
            logger.error(f"API Error for {city_name}: Status {response.status_code} - {response.text}")
            return None

    except requests.exceptions.Timeout:
        logger.error(f"Timeout occurred while connecting to weather API for {city_name} ({timeout}s)")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching weather for {city_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error for {city_name}: {e}")
        return None

def save_raw_json(data, filepath):
    """Saves raw data payload to disk with error handling."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Saved {len(data)} city records to {filepath}")
        return True
    except IOError as e:
        logger.error(f"Failed to write raw data to {filepath}: {e}")
        return False

def extract_all():
    """Main extraction routine: loops over configured cities and saves raw JSON."""
    config = load_config()
    cities = config.get("cities", [])
    raw_dir = config.get("paths", {}).get("raw_data_dir", "data/raw")

    session = create_retry_session(
        retries=config.get("api", {}).get("max_retries", 3),
        backoff_factor=config.get("api", {}).get("backoff_factor", 1.5)
    )

    all_weather_data = []
    logger.info(f"Starting extraction for {len(cities)} cities...")

    for city in cities:
        weather = fetch_weather(city["name"], city["lat"], city["lon"], session=session, config=config)
        if weather:
            all_weather_data.append(weather)

    if all_weather_data:
        # Save standard master file
        standard_path = os.path.join(raw_dir, "weather_raw.json")
        save_raw_json(all_weather_data, standard_path)

        # Save historical timestamped snapshot (Data Lake pattern)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = os.path.join(raw_dir, f"weather_{timestamp_str}.json")
        save_raw_json(all_weather_data, snapshot_path)

        logger.info(f"Extraction complete! Collected {len(all_weather_data)}/{len(cities)} cities.")
        return standard_path
    else:
        logger.warning("Extraction finished with 0 records collected.")
        return None

if __name__ == "__main__":
    extract_all()
