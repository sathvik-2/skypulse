import os
import json
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from pipeline.utils.config import load_config
from pipeline.utils.logger import get_logger

logger = get_logger("mongo_staging")

def store_raw_in_mongo(raw_filepath=None, raw_data=None):
    """
    Stores raw weather JSON payloads in MongoDB collection as a Raw Data Lake.
    Gracefully logs and skips if local MongoDB server is not running.
    """
    config = load_config()
    mongo_cfg = config.get("database", {}).get("mongodb", {})
    host = mongo_cfg.get("host", "localhost")
    port = mongo_cfg.get("port", 27017)
    db_name = mongo_cfg.get("database", "weather_lake")
    coll_name = mongo_cfg.get("collection", "raw_weather")

    # Load data from file if not directly provided
    if raw_data is None:
        if raw_filepath is None:
            raw_filepath = os.path.join(config.get("paths", {}).get("raw_data_dir", "data/raw"), "weather_raw.json")
        if not os.path.exists(raw_filepath):
            logger.warning(f"Raw file {raw_filepath} not found for MongoDB staging.")
            return False

        with open(raw_filepath, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

    if not isinstance(raw_data, list):
        raw_data = [raw_data]

    try:
        # Connect with a fast 2-second timeout to avoid stalling if Mongo isn't running
        client = MongoClient(host=host, port=port, serverSelectionTimeoutMS=2000)
        # Probe server status
        client.admin.command('ping')
        
        db = client[db_name]
        collection = db[coll_name]

        # Attach metadata to documents
        documents = []
        for doc in raw_data:
            doc_copy = dict(doc)
            doc_copy["_staged_at"] = datetime.utcnow()
            documents.append(doc_copy)

        result = collection.insert_many(documents)
        logger.info(f"MongoDB Lake: Staged {len(result.inserted_ids)} raw documents into '{db_name}.{coll_name}'.")
        client.close()
        return True

    except (ServerSelectionTimeoutError, ConnectionRefusedError):
        logger.info("MongoDB service is not currently running. Skipping optional Raw Lake staging.")
        return False
    except PyMongoError as e:
        logger.warning(f"MongoDB error: {e}. Skipping raw staging.")
        return False
    except Exception as e:
        logger.warning(f"Unexpected MongoDB staging error: {e}")
        return False

if __name__ == "__main__":
    store_raw_in_mongo()
