import os
import pandas as pd
import pymysql

from pipeline.utils.config import load_config
from pipeline.utils.logger import get_logger

logger = get_logger("load_sql")

def get_connection(database=None):
    """Establishes connection to MySQL server using configuration."""
    config = load_config()
    mysql_cfg = config.get("database", {}).get("mysql", {})
    
    conn_params = {
        "host": mysql_cfg.get("host", "localhost"),
        "port": mysql_cfg.get("port", 3306),
        "user": mysql_cfg.get("user", "root"),
        "password": mysql_cfg.get("password", ""),
        "autocommit": True
    }
    if database:
        conn_params["database"] = database
        
    return pymysql.connect(**conn_params)

def init_db(schema_path="sql/schema.sql"):
    """Executes the DDL schema to ensure database and tables exist."""
    logger.info("Initializing MySQL database schema...")
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            if not os.path.exists(schema_path):
                logger.error(f"Schema file '{schema_path}' not found!")
                return False

            with open(schema_path, "r", encoding="utf-8") as f:
                sql_script = f.read()

            for statement in sql_script.split(";"):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)

        conn.close()
        logger.info("Database and table 'weather_records' are verified and ready.")
        return True
    except pymysql.MySQLError as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def load_data(csv_filepath=None):
    """Reads clean CSV and loads rows into MySQL with duplicate protection."""
    config = load_config()
    if csv_filepath is None:
        csv_filepath = os.path.join(
            config.get("paths", {}).get("processed_data_dir", "data/processed"),
            "weather_clean.csv"
        )

    if not os.path.exists(csv_filepath):
        logger.error(f"Processed CSV file '{csv_filepath}' does not exist.")
        return 0

    df = pd.read_csv(csv_filepath)
    if df.empty:
        logger.warning(f"CSV file '{csv_filepath}' has no rows to load.")
        return 0

    db_name = config.get("database", {}).get("mysql", {}).get("database", "weather_db")
    
    insert_query = """
    INSERT INTO weather_records (city, date, temperature, humidity, precipitation)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        temperature = VALUES(temperature),
        humidity = VALUES(humidity),
        precipitation = VALUES(precipitation);
    """

    try:
        conn = get_connection(database=db_name)
        rows_affected = 0

        with conn.cursor() as cursor:
            for _, row in df.iterrows():
                cursor.execute(insert_query, (
                    row["city"],
                    row["date"],
                    float(row["temperature"]),
                    int(row["humidity"]),
                    float(row["precipitation"])
                ))
                rows_affected += 1

        conn.close()
        logger.info(f"Successfully upserted {rows_affected} records into MySQL ({db_name}.weather_records)!")
        return rows_affected
    except pymysql.MySQLError as e:
        logger.error(f"MySQL error while loading data: {e}")
        return 0

def verify_records():
    """Prints database summary of current records per city."""
    config = load_config()
    db_name = config.get("database", {}).get("mysql", {}).get("database", "weather_db")
    try:
        conn = get_connection(database=db_name)
        with conn.cursor() as cursor:
            cursor.execute("SELECT city, COUNT(*) FROM weather_records GROUP BY city ORDER BY city;")
            results = cursor.fetchall()
            logger.info("Current verified records in MySQL:")
            for city, count in results:
                logger.info(f"  • {city}: {count} row(s)")
        conn.close()
    except Exception as e:
        logger.error(f"Could not verify records: {e}")

if __name__ == "__main__":
    init_db()
    load_data()
    verify_records()
