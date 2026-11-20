"""
SkyPulse Weather - Consumer-Facing Interactive Weather Web App Backend
Supports global city search, live atmospheric observations, 24-hour hourly forecast,
7-day daily outlook, dual AQI standards (Indian CPCB/aqi.in + US EPA), and MySQL auto-ingestion.
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

def calc_cpcb_subindex(conc, breakpoints):
    """Calculates linear sub-index for Indian CPCB National AQI."""
    for (c_low, c_high, i_low, i_high) in breakpoints:
        if c_low <= conc <= c_high:
            return i_low + ((i_high - i_low) / (c_high - c_low)) * (conc - c_low)
    # Beyond highest breakpoint
    if conc > breakpoints[-1][1]:
        return 500
    return 0

def calculate_indian_cpcb_aqi(pm25, pm10):
    """
    Calculates Indian National Air Quality Index (NAQI) as defined by CPCB (used by aqi.in).
    """
    pm25_bp = [
        (0, 30, 0, 50),
        (31, 60, 51, 100),
        (61, 90, 101, 200),
        (91, 120, 201, 300),
        (121, 250, 301, 400),
        (251, 350, 401, 500)
    ]
    pm10_bp = [
        (0, 50, 0, 50),
        (51, 100, 51, 100),
        (101, 250, 101, 200),
        (251, 350, 201, 300),
        (351, 430, 301, 400),
        (431, 500, 401, 500)
    ]

    i_pm25 = calc_cpcb_subindex(pm25, pm25_bp)
    i_pm10 = calc_cpcb_subindex(pm10, pm10_bp)

    aqi_val = round(max(i_pm25, i_pm10))

    if aqi_val <= 50:
        return {
            "value": aqi_val,
            "status": "Good",
            "text_color": "text-emerald-400",
            "bg_color": "bg-emerald-500/10",
            "border_color": "border-emerald-500/30",
            "desc": "Air quality is good. Minimal impact on health.",
            "percent": min(100, int((aqi_val / 300) * 100)),
            "standard_name": "Indian CPCB (aqi.in standard)"
        }
    elif aqi_val <= 100:
        return {
            "value": aqi_val,
            "status": "Satisfactory",
            "text_color": "text-emerald-300",
            "bg_color": "bg-emerald-500/10",
            "border_color": "border-emerald-500/30",
            "desc": "Minor breathing discomfort to sensitive people. Satisfactory for general public.",
            "percent": min(100, int((aqi_val / 300) * 100)),
            "standard_name": "Indian CPCB (aqi.in standard)"
        }
    elif aqi_val <= 200:
        return {
            "value": aqi_val,
            "status": "Moderate",
            "text_color": "text-yellow-400",
            "bg_color": "bg-yellow-500/10",
            "border_color": "border-yellow-500/30",
            "desc": "Breathing discomfort to people with lung, asthma and heart diseases.",
            "percent": min(100, int((aqi_val / 300) * 100)),
            "standard_name": "Indian CPCB (aqi.in standard)"
        }
    elif aqi_val <= 300:
        return {
            "value": aqi_val,
            "status": "Poor",
            "text_color": "text-orange-400",
            "bg_color": "bg-orange-500/10",
            "border_color": "border-orange-500/30",
            "desc": "Breathing discomfort to most people on prolonged exposure.",
            "percent": min(100, int((aqi_val / 300) * 100)),
            "standard_name": "Indian CPCB (aqi.in standard)"
        }
    elif aqi_val <= 400:
        return {
            "value": aqi_val,
            "status": "Very Poor",
            "text_color": "text-rose-400",
            "bg_color": "bg-rose-500/10",
            "border_color": "border-rose-500/30",
            "desc": "Respiratory illness on prolonged exposure. Pronounced effect on lung patients.",
            "percent": min(100, int((aqi_val / 300) * 100)),
            "standard_name": "Indian CPCB (aqi.in standard)"
        }
    else:
        return {
            "value": aqi_val,
            "status": "Severe",
            "text_color": "text-red-500",
            "bg_color": "bg-red-950/40",
            "border_color": "border-red-500/50",
            "desc": "Affects healthy people and seriously impacts those with existing diseases.",
            "percent": 100,
            "standard_name": "Indian CPCB (aqi.in standard)"
        }

def get_us_aqi_details(aqi_val):
    """Categorizes US EPA AQI index (0-500)."""
    if aqi_val <= 50:
        return {
            "value": aqi_val,
            "status": "Good",
            "text_color": "text-emerald-400",
            "bg_color": "bg-emerald-500/10",
            "border_color": "border-emerald-500/30",
            "desc": "Air quality is satisfactory with little to no risk.",
            "percent": min(100, int((aqi_val / 300) * 100)),
            "standard_name": "US EPA Standard"
        }
    elif aqi_val <= 100:
        return {
            "value": aqi_val,
            "status": "Moderate",
            "text_color": "text-yellow-400",
            "bg_color": "bg-yellow-500/10",
            "border_color": "border-yellow-500/30",
            "desc": "Acceptable air quality; very sensitive people may feel mild irritation.",
            "percent": min(100, int((aqi_val / 300) * 100)),
            "standard_name": "US EPA Standard"
        }
    elif aqi_val <= 150:
        return {
            "value": aqi_val,
            "status": "Unhealthy for Sensitive Groups",
            "text_color": "text-orange-400",
            "bg_color": "bg-orange-500/10",
            "border_color": "border-orange-500/30",
            "desc": "Members of sensitive groups may experience health effects.",
            "percent": min(100, int((aqi_val / 300) * 100)),
            "standard_name": "US EPA Standard"
        }
    elif aqi_val <= 200:
        return {
            "value": aqi_val,
            "status": "Unhealthy",
            "text_color": "text-rose-400",
            "bg_color": "bg-rose-500/10",
            "border_color": "border-rose-500/30",
            "desc": "Everyone may begin to experience adverse health effects.",
            "percent": min(100, int((aqi_val / 300) * 100)),
            "standard_name": "US EPA Standard"
        }
    elif aqi_val <= 300:
        return {
            "value": aqi_val,
            "status": "Very Unhealthy",
            "text_color": "text-purple-400",
            "bg_color": "bg-purple-500/10",
            "border_color": "border-purple-500/30",
            "desc": "Health alert: The risk of health effects is substantially increased.",
            "percent": min(100, int((aqi_val / 300) * 100)),
            "standard_name": "US EPA Standard"
        }
    else:
        return {
            "value": aqi_val,
            "status": "Hazardous",
            "text_color": "text-red-500",
            "bg_color": "bg-red-950/40",
            "border_color": "border-red-500/50",
            "desc": "Health warning of emergency conditions.",
            "percent": 100,
            "standard_name": "US EPA Standard"
        }

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
        pass

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
    Fetches real-time weather & dual AQI (Indian CPCB and US EPA).
    """
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    city_name = request.args.get("city", "Selected Location")

    if lat is None or lon is None:
        lat, lon, city_name = 12.9716, 77.5946, "Bengaluru"

    try:
        # 1. Weather Forecast
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,surface_pressure",
            "hourly": "temperature_2m,weather_code,precipitation_probability",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum",
            "timezone": "auto",
            "forecast_days": 7
        }
        res_weather = requests.get(weather_url, params=weather_params, timeout=6)
        if res_weather.status_code != 200:
            return jsonify({"error": "Failed to fetch weather data"}), 500

        data = res_weather.json()
        current = data.get("current", {})
        hourly = data.get("hourly", {})
        daily = data.get("daily", {})

        weather_code = current.get("weather_code", 0)
        weather_info = get_weather_info(weather_code)

        # 2. Air Quality Index (Both Indian CPCB & US EPA)
        pm2_5_val = 25.0
        pm10_val = 40.0
        no2_val = 15.0
        o3_val = 30.0
        raw_us_aqi = 65

        try:
            aqi_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
            aqi_params = {
                "latitude": lat,
                "longitude": lon,
                "current": "us_aqi,pm10,pm2_5,nitrogen_dioxide,ozone"
            }
            res_aqi = requests.get(aqi_url, params=aqi_params, timeout=4)
            if res_aqi.status_code == 200:
                aqi_curr = res_aqi.json().get("current", {})
                pm2_5_val = round(aqi_curr.get("pm2_5", 25.0), 1)
                pm10_val = round(aqi_curr.get("pm10", 40.0), 1)
                no2_val = round(aqi_curr.get("nitrogen_dioxide", 15.0), 1)
                o3_val = round(aqi_curr.get("ozone", 30.0), 1)
                raw_us_aqi = int(aqi_curr.get("us_aqi", 65))
        except Exception:
            pass

        # Calculate Indian CPCB standard (matches aqi.in)
        cpcb_aqi_details = calculate_indian_cpcb_aqi(pm2_5_val, pm10_val)
        # Calculate US EPA standard
        us_aqi_details = get_us_aqi_details(raw_us_aqi)

        aqi_payload = {
            "indian": cpcb_aqi_details,
            "us": us_aqi_details,
            "pm2_5": pm2_5_val,
            "pm10": pm10_val,
            "no2": no2_val,
            "o3": o3_val
        }

        # Build current weather object
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

        # Build 24-Hour Forecast
        hourly_list = []
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        codes = hourly.get("weather_code", [])
        pop = hourly.get("precipitation_probability", [])

        now_hour_str = datetime.now().strftime("%Y-%m-%dT%H:00")
        start_idx = 0
        for i, t in enumerate(times):
            if t >= now_hour_str:
                start_idx = i
                break

        for i in range(start_idx, min(start_idx + 24, len(times))):
            h_code = codes[i] if i < len(codes) else 0
            h_info = get_weather_info(h_code)
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
            "aqi": aqi_payload,
            "hourly": hourly_list,
            "daily": daily_list
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
