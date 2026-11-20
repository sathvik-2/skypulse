import os
import yaml
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")

def load_config():
    """Loads configuration from config.yaml, allowing environment variable overrides."""
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # Override with environment variables if available
    mysql_cfg = config.get("database", {}).get("mysql", {})
    if os.getenv("MYSQL_HOST"):
        mysql_cfg["host"] = os.getenv("MYSQL_HOST")
    if os.getenv("MYSQL_USER"):
        mysql_cfg["user"] = os.getenv("MYSQL_USER")
    if os.getenv("MYSQL_PASSWORD"):
        mysql_cfg["password"] = os.getenv("MYSQL_PASSWORD")
    if os.getenv("MYSQL_DATABASE"):
        mysql_cfg["database"] = os.getenv("MYSQL_DATABASE")
        
    return config
