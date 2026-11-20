-- 1. Create the database if it doesn't already exist
CREATE DATABASE IF NOT EXISTS weather_db;

-- 2. Tell MySQL to use this database for the commands below
USE weather_db;

-- 3. Create our table with columns and constraints
CREATE TABLE IF NOT EXISTS weather_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(50) NOT NULL,
    date DATETIME NOT NULL,
    temperature FLOAT NOT NULL,
    humidity INT NOT NULL,
    precipitation FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- The duplicate prevention constraint:
    UNIQUE KEY unique_city_date (city, date)
);