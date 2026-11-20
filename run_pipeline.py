"""
NimbusFlow Master Weather Pipeline Orchestrator
Runs: Extract -> Raw Staging (Mongo) -> Transform -> Load (MySQL) -> Health Check
Usage:
    python run_pipeline.py
"""

import sys
import os
import time

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from pipeline.utils.logger import get_logger
from pipeline.utils.config import load_config
from pipeline.extract import extract_all
from pipeline.store_mongo import store_raw_in_mongo
from pipeline.transform import clean_weather_data
from pipeline.load_sql import init_db, load_data, verify_records

logger = get_logger("orchestrator")

def run_pipeline():
    start_time = time.time()
    config = load_config()

    print("\n" + "=" * 65)
    print(f"🚀 STARTING PIPELINE RUN: {config.get('app', {}).get('name', 'NimbusFlow')}")
    print("=" * 65 + "\n")

    # Step 1: Extract
    logger.info("=== STEP 1 / 4: EXTRACTION ===")
    raw_path = extract_all()
    if not raw_path:
        logger.error("Pipeline stopped: Extraction produced no data.")
        return False

    # Step 2: Optional Raw Data Lake Staging
    logger.info("=== STEP 2 / 4: RAW DATA LAKE STAGING ===")
    store_raw_in_mongo(raw_filepath=raw_path)

    # Step 3: Transform
    logger.info("=== STEP 3 / 4: TRANSFORMATION ===")
    df = clean_weather_data(raw_filepath=raw_path)
    if df is None or df.empty:
        logger.error("Pipeline stopped: Transformation failed.")
        return False

    # Step 4: Load into Relational Database
    logger.info("=== STEP 4 / 4: RELATIONAL DATABASE LOAD ===")
    init_db()
    rows_loaded = load_data()

    # Step 5: Verification
    verify_records()

    duration = round(time.time() - start_time, 2)
    print("\n" + "=" * 65)
    logger.info(f"🎉 PIPELINE RUN COMPLETED SUCCESSFULLY in {duration}s! ({rows_loaded} records processed)")
    print("=" * 65 + "\n")
    return True

if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)
