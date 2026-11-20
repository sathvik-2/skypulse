"""
Nimbus Weather - Consumer-Facing Interactive Weather Web App Backend
Supports global city search, live atmospheric observations, 24-hour hourly forecast,
7-day daily outlook, and auto-ingestion into MySQL.
"""

import os
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import requests
import pymysql

from pipeline.utils.config import load_config

app = Flask(__name__)

# Weather code mapping to friendly text and Lucide icon names
WEATHER_CODE_MAP = {
    0: {"label": "Clear Sky", "icon": "sun", "color": "text-amber-400"},
    1: {"label": "Mainly Clear", "icon": "sun-medium", "color": "text-amber-300"},
    2: {"label": "Partly Cloudy", "icon": "cloud-sun", "color": "text-sky-300"},
    3: {"label": "Overcast", "icon": "cloud", "color": "text-slate-400"},
    45: {"label": "Foggy", "icon": "cloud-fog", "color": "text-slate-400"},
    48: {"label": "Rime Fog", "icon": "cloud-fog", "color": "text-slate-400"},
    51: {"label": "Light Drizzle", "icon": "cloud-drizzle", "color": "text-blue-300"},
    53: {"label": "Moderate Drizzle", "icon": "cloud-drizzle", "color": "text-blue-400"},
    55: {"label": "Dense Drizzle", "icon": "cloud-rain", "color": "text-blue-500"},
    61: {"label": "Slight Rain", "icon": "cloud-rain", "color": "text-cyan-400"},
    63: {"label": "Moderate Rain", "icon": "cloud-rain", "color": "text-cyan-500"},
    65: {"label": "Heavy Rain", "icon": "cloud-rain-wind", "color": "text-indigo-400"},
    71: {"label": "Slight Snow", "icon": "cloud-snow", "color": "text-indigo-200"},
    73: {"label": "Moderate Snow", "icon": "snowflake", "color": "text-indigo-100"},
    75: {"label": "Heavy Snow", "icon": "snowflake", "color": "text-white"},
    80: {"label": "Rain Showers", "icon": "cloud-rain", "color": "text-cyan-400"},
    81: {"label": "Moderate Showers", "icon": "cloud-rain", "color": "text-blue-400"},
    82: {"label": "Violent Showers", "icon": "cloud-lightning", "color": "text-purple-400"},
    95: {"label": "Thunderstorm", "icon": "zap", "color": "text-amber-400"},
    96: {"label": "Thunderstorm & Hail", "icon": "cloud-lightning", "color": "text-purple-400"},
    99: {"label": "Severe Storm", "icon": "tornado", "color": "text-rose-400"}
}

def get_weather_info(code):
    return WEATHER_CODE_MAP.get(code, {"label": "Clear", "icon": "sun", "color": "text-amber-400"})

def save_to_db(city, dt, temp, humidity, precipitation):
    """Silently saves/upserts the searched city reading into MySQL database."""
    config = load_config()
    mysql_cfg = config.get("database", {}).get("mysql", {})
    try:
        conn = pymysql.connect(
            host=mysql_cfg.get("host", "localhost"),
            port=mysql_cfg.get("port", 3306),
            user=mysql_cfg.get("user", "root"),
            password=mysql_cfg.get("password", ""),
            database=mysql_cfg.get("database", "weather_db"),
            autocommit=True
        )
        with conn.cursor() as cur:
            query = """
            INSERT INTO weather_records (city, date, temperature, humidity, precipitation)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                temperature = VALUES(temperature),
                humidity = VALUES(humidity),
                precipitation = VALUES(precipitation);
            """
            cur.execute(query, (city, dt, temp, humidity, precipitation))
        conn.close()
    except Exception:
        pass  # Don't fail the user UI if MySQL is briefly unreachable

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/search")
def search_cities():
    """Search for global cities by query text using Open-Meteo Geocoding API."""
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify([])

    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={query}&count=6&language=en&format=json"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            results = []
            for item in data.get("results", []):
                admin = item.get("admin1", "")
                country = item.get("country", "")
                label = f"{item['name']}, {admin}, {country}" if admin else f"{item['name']}, {country}"
                results.append({
                    "name": item["name"],
                    "country": country,
                    "state": admin,
                    "label": label,
                    "lat": item["latitude"],
                    "lon": item["longitude"],
                    "timezone": item.get("timezone", "auto")
                })
            return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify([])

@app.route("/api/weather")
def get_weather():
    """
    Fetches rich real-time, 24h hourly, and 7-day daily weather for latitude & longitude.
    """
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    city_name = request.args.get("city", "Selected Location")

    if lat is None or lon is None:
        # Default to Bengaluru if no coords passed
        lat, lon, city_name = 12.9716, 77.5946, "Bengaluru"

    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,surface_pressure",
            "hourly": "temperature_2m,weather_code,precipitation_probability",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum",
            "timezone": "auto",
            "forecast_days": 7
        }
        res = requests.get(url, params=params, timeout=6)
        if res.status_code != 200:
            return jsonify({"error": "Failed to fetch weather data from service"}), 500

        data = res.json()
        current = data.get("current", {})
        hourly = data.get("hourly", {})
        daily = data.get("daily", {})

        weather_code = current.get("weather_code", 0)
        weather_info = get_weather_info(weather_code)

        # Build clean current object
        current_obj = {
            "city": city_name,
            "temperature": round(current.get("temperature_2m", 0.0), 1),
            "feels_like": round(current.get("apparent_temperature", 0.0), 1),
            "humidity": current.get("relative_humidity_2m", 0),
            "precipitation": current.get("precipitation", 0.0),
            "wind_speed": round(current.get("wind_speed_10m", 0.0), 1),
            "pressure": round(current.get("surface_pressure", 1013), 0),
            "condition": weather_info["label"],
            "icon": weather_info["icon"],
            "color": weather_info["color"],
            "time": current.get("time", datetime.now().isoformat())
        }

        # Build 24-Hour Forecast (next 24 hours from now)
        hourly_list = []
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        codes = hourly.get("weather_code", [])
        pop = hourly.get("precipitation_probability", [])

        # Find starting index close to current time
        now_hour_str = datetime.now().strftime("%Y-%m-%dT%H:00")
        start_idx = 0
        for i, t in enumerate(times):
            if t >= now_hour_str:
                start_idx = i
                break

        for i in range(start_idx, min(start_idx + 24, len(times))):
            h_code = codes[i] if i < len(codes) else 0
            h_info = get_weather_info(h_code)
            # Parse hour like "2 PM"
            dt_h = datetime.fromisoformat(times[i])
            hourly_list.append({
                "time": dt_h.strftime("%I %p").lstrip("0"),
                "temp": round(temps[i], 1) if i < len(temps) else 0,
                "icon": h_info["icon"],
                "color": h_info["color"],
                "pop": pop[i] if i < len(pop) else 0
            })

        # Build 7-Day Forecast
        daily_list = []
        d_times = daily.get("time", [])
        d_max = daily.get("temperature_2m_max", [])
        d_min = daily.get("temperature_2m_min", [])
        d_codes = daily.get("weather_code", [])
        d_rain = daily.get("precipitation_sum", [])
        d_sunrise = daily.get("sunrise", [])
        d_sunset = daily.get("sunset", [])

        for i in range(len(d_times)):
            d_code = d_codes[i] if i < len(d_codes) else 0
            d_info = get_weather_info(d_code)
            dt_d = datetime.fromisoformat(d_times[i])
            day_label = "Today" if i == 0 else dt_d.strftime("%a")
            daily_list.append({
                "date": d_times[i],
                "day": day_label,
                "max_temp": round(d_max[i], 1) if i < len(d_max) else 0,
                "min_temp": round(d_min[i], 1) if i < len(d_min) else 0,
                "condition": d_info["label"],
                "icon": d_info["icon"],
                "color": d_info["color"],
                "rain": round(d_rain[i], 1) if i < len(d_rain) else 0
            })

        # Today's sunrise & sunset
        sunrise_str = ""
        sunset_str = ""
        if d_sunrise and len(d_sunrise) > 0:
            sunrise_str = datetime.fromisoformat(d_sunrise[0]).strftime("%I:%M %p").lstrip("0")
        if d_sunset and len(d_sunset) > 0:
            sunset_str = datetime.fromisoformat(d_sunset[0]).strftime("%I:%M %p").lstrip("0")

        current_obj["today_max"] = daily_list[0]["max_temp"] if daily_list else current_obj["temperature"]
        current_obj["today_min"] = daily_list[0]["min_temp"] if daily_list else current_obj["temperature"]
        current_obj["sunrise"] = sunrise_str
        current_obj["sunset"] = sunset_str

        # Auto-ingest into MySQL in background
        db_time = current.get("time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")).replace("T", " ")
        if len(db_time) == 16:
            db_time += ":00"
        save_to_db(city_name, db_time, current_obj["temperature"], current_obj["humidity"], current_obj["precipitation"])

        return jsonify({
            "current": current_obj,
            "hourly": hourly_list,
            "daily": daily_list
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
