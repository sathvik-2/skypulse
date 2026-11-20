-- ============================================================
-- NimbusFlow Weather Pipeline: Advanced SQL Analytics
-- Demonstrating Aggregations, Window Functions, and Ranking
-- ============================================================

USE weather_db;

-- ------------------------------------------------------------
-- Query 1: Overview Summary - Average, Min, Max Temp & Rainfall per City
-- ------------------------------------------------------------
SELECT 
    city,
    COUNT(*) AS total_readings,
    ROUND(AVG(temperature), 2) AS avg_temperature_c,
    ROUND(MIN(temperature), 2) AS min_temperature_c,
    ROUND(MAX(temperature), 2) AS max_temperature_c,
    ROUND(AVG(humidity), 1) AS avg_humidity_pct,
    ROUND(SUM(precipitation), 2) AS total_rainfall_mm
FROM weather_records
GROUP BY city
ORDER BY avg_temperature_c DESC;


-- ------------------------------------------------------------
-- Query 2: The Hottest Day for Each City (Using ROW_NUMBER Window Function)
-- ------------------------------------------------------------
WITH RankedWeather AS (
    SELECT 
        city,
        date,
        temperature,
        humidity,
        ROW_NUMBER() OVER (
            PARTITION BY city 
            ORDER BY temperature DESC
        ) AS temp_rank
    FROM weather_records
)
SELECT 
    city,
    date AS hottest_recorded_time,
    temperature AS peak_temperature_c,
    humidity AS humidity_at_peak
FROM RankedWeather
WHERE temp_rank = 1
ORDER BY peak_temperature_c DESC;


-- ------------------------------------------------------------
-- Query 3: 7-Day Rolling Average Temperature per City (Window Function)
-- Calculates the smoothed moving average across daily records
-- ------------------------------------------------------------
SELECT 
    city,
    date,
    temperature AS daily_temp_c,
    ROUND(
        AVG(temperature) OVER (
            PARTITION BY city 
            ORDER BY date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_7day_avg_temp_c
FROM weather_records
ORDER BY city, date;
