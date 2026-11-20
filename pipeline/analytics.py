"""
NimbusFlow SQL Analytics Runner
Executes the analytical queries and window functions against MySQL and prints clean reports.
Usage:
    python pipeline/analytics.py
"""

import sys
import os
import pandas as pd
import pymysql

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from pipeline.utils.config import load_config
from pipeline.utils.logger import get_logger

logger = get_logger("analytics")

def run_analytics():
    config = load_config()
    mysql_cfg = config.get("database", {}).get("mysql", {})

    conn = pymysql.connect(
        host=mysql_cfg.get("host", "localhost"),
        port=mysql_cfg.get("port", 3306),
        user=mysql_cfg.get("user", "root"),
        password=mysql_cfg.get("password", ""),
        database=mysql_cfg.get("database", "weather_db")
    )

    print("\n" + "=" * 70)
    print("📊 NIMBUSFLOW SQL ANALYTICS REPORT")
    print("=" * 70)

    # 1. Summary Statistics
    q1 = """
    SELECT 
        city,
        COUNT(*) AS readings,
        ROUND(AVG(temperature), 1) AS avg_temp,
        ROUND(MIN(temperature), 1) AS min_temp,
        ROUND(MAX(temperature), 1) AS max_temp,
        ROUND(AVG(humidity), 0) AS avg_humidity,
        ROUND(SUM(precipitation), 2) AS total_rain
    FROM weather_records
    GROUP BY city
    ORDER BY avg_temp DESC;
    """
    df_summary = pd.read_sql(q1, conn)
    print("\n📈 1. City Summary Statistics (°C, %, mm):")
    print(df_summary.to_string(index=False))

    # 2. Hottest Day per City (Window Function)
    q2 = """
    WITH RankedWeather AS (
        SELECT 
            city,
            date,
            temperature,
            ROW_NUMBER() OVER (PARTITION BY city ORDER BY temperature DESC) AS temp_rank
        FROM weather_records
    )
    SELECT city, date, temperature AS peak_temp
    FROM RankedWeather
    WHERE temp_rank = 1
    ORDER BY peak_temp DESC;
    """
    df_hottest = pd.read_sql(q2, conn)
    print("\n🔥 2. Hottest Recorded Day per City (ROW_NUMBER Window Function):")
    print(df_hottest.to_string(index=False))

    # 3. Rolling Average Window Function
    q3 = """
    SELECT 
        city,
        date,
        temperature,
        ROUND(AVG(temperature) OVER (
            PARTITION BY city 
            ORDER BY date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ), 2) AS rolling_7d_avg
    FROM weather_records
    ORDER BY city, date
    LIMIT 15;
    """
    df_rolling = pd.read_sql(q3, conn)
    print("\n🌊 3. 7-Day Rolling Average Temperature (Moving Window Function - Sample):")
    print(df_rolling.to_string(index=False))

    print("\n" + "=" * 70 + "\n")
    conn.close()

if __name__ == "__main__":
    run_analytics()
