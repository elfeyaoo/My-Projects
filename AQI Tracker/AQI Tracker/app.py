from flask import Flask, render_template, request, jsonify, send_file
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import io
import base64
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta
import pytz

app = Flask(__name__, template_folder="templates")

import matplotlib
matplotlib.use('Agg')  # Use a non-GUI backend before importing pyplot
import matplotlib.pyplot as plt


# API KEYS
WEATHER_API_KEY = "032fd7c4a21bae649bd84cf3ab5b2342"
AQI_API_KEY = "842ba045f34f90b82db9ceda40908626"

# API BASE URLS
WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/"
AIR_POLLUTION_BASE_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

# Function to fetch current weather data
def get_current_weather(city):
    url = f"{WEATHER_BASE_URL}weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()

    if response.status_code != 200:
        return None

    return {
        "city": data["name"],
        "current_temp": round(data["main"]["temp"]),
        "feels_like": round(data["main"]["feels_like"]),
        "temp_min": round(data["main"]["temp_min"]),
        "temp_max": round(data["main"]["temp_max"]),
        "humidity": data["main"]["humidity"],
        "description": data["weather"][0]["description"],
        "country": data["sys"]["country"],
        "wind_speed": data["wind"]["speed"],
        "pressure": data["main"]["pressure"],
        "lat": data["coord"]["lat"],
        "lon": data["coord"]["lon"],
    }

# Function to fetch AQI data
def get_aqi_data(lat, lon):
    url = f"{AIR_POLLUTION_BASE_URL}?lat={lat}&lon={lon}&appid={AQI_API_KEY}"
    response = requests.get(url)

    if response.status_code != 200:
        return None

    data = response.json()

    if "list" not in data or not data["list"]:
        return None

    aqi_index = data["list"][0]["main"]["aqi"]

    # Correct AQI level mapping as per OpenWeather
    aqi_levels = {
        1: "Good",
        2: "Fair",
        3: "Moderate",
        4: "Poor",
        5: "Very Poor"
    }

    return {
        "aqi_index": aqi_index,
        "aqi_description": aqi_levels.get(aqi_index, "Unknown"),  # Handles unexpected values
        "pm2_5": data["list"][0]["components"].get("pm2_5", "N/A"),
        "pm10": data["list"][0]["components"].get("pm10", "N/A"),
        "co": data["list"][0]["components"].get("co", "N/A"),
        "no2": data["list"][0]["components"].get("no2", "N/A"),
        "so2": data["list"][0]["components"].get("so2", "N/A"),
        "o3": data["list"][0]["components"].get("o3", "N/A"),
    }


# Read historical weather data
def read_historical_weather_data():
    return pd.read_csv(r'C:\Users\Avadhoot\Desktop\AQI\weather.csv').dropna().drop_duplicates()

# Read historical AQI data
def read_historical_aqi_data():
    df = pd.read_csv("aqi.csv").dropna(subset=["PM10 (ug/m3)", "Ozone (ug/m3)", "NO2 (ug/m3)"]).drop_duplicates()
    df.columns = df.columns.str.strip()  # Ensure column names are clean

    print("🔍 AQI CSV Columns:", df.columns)  # Debugging Output
    return df

# Prepare regression data for weather
def prepare_regression_data(data, feature):
    x, y = [], []
    for i in range(len(data) - 1):
        x.append(data[feature].iloc[i])
        y.append(data[feature].iloc[i + 1])
    return np.array(x).reshape(-1, 1), np.array(y)

# Prepare regression data for PM10, O3, and SO2
def prepare_pollutant_regression(data, feature):
    if feature not in data.columns:
        raise ValueError(f"Feature '{feature}' not found in data columns.")
    x = data[feature].iloc[:-1].values.reshape(-1, 1)
    y = data[feature].iloc[1:].values
    return x, y

# Predict future values for weather
def predict_future(model, current_value):
    predictions = [current_value]
    for _ in range(12):
        next_value = model.predict(np.array([[predictions[-1]]]))
        predictions.append(next_value[0])
    return predictions[1:]

# Predict future pollutant values
def predict_future_pollutants(model, current_value):
    predictions = [current_value]
    for _ in range(12):  # Predict for 12 months
        next_value = model.predict(np.array([[predictions[-1]]]))
        predictions.append(next_value[0])
    return predictions[1:]

@app.route("/")
def home():
    return render_template("index.html")

# ✅ Put your GNews API Key here
NEWS_API_KEY = "e10f12e27b6d4266beb55d7cc746150a"

def get_news_by_topic(topic, page_size=10):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": topic,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": NEWS_API_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data.get("articles", [])

@app.route("/weather")
def weather_page():
    weather_news = get_news_by_topic("weather forecast OR climate change")
    return render_template("weather.html", weather_news=weather_news)


@app.route("/aqi")
def aqi_page():
    aqi_news = get_news_by_topic("air quality OR air pollution")
    return render_template("aqi.html", aqi_news=aqi_news)


@app.route("/get_weather", methods=["POST"])
def get_weather():
    city = request.form.get("city")
    weather_data = get_current_weather(city)

    if not weather_data:
        return jsonify({"error": "City not found"}), 400

    historical_data = read_historical_weather_data()
    X_temp, y_temp = prepare_regression_data(historical_data, "Temp")
    X_hum, y_hum = prepare_regression_data(historical_data, "Humidity")

    temp_model = RandomForestRegressor(n_estimators=100, random_state=42)
    temp_model.fit(X_temp, y_temp)

    hum_model = RandomForestRegressor(n_estimators=100, random_state=42)
    hum_model.fit(X_hum, y_hum)

    future_temp = predict_future(temp_model, weather_data["temp_min"])
    future_humidity = predict_future(hum_model, weather_data["humidity"])

    timezone = pytz.timezone("Asia/Kolkata")
    now = datetime.now(timezone)
    future_months = [(now + timedelta(days=30 * i)).strftime("%b %Y") for i in range(1, 13)]

    plot_path = generate_plots(city, future_months, future_temp, future_humidity)

    return jsonify({
        "current_weather": weather_data,
        "future_temp": list(map(lambda x: round(x, 1), future_temp)),
        "future_humidity": list(map(lambda x: round(x, 1), future_humidity)),
        "future_months": future_months,
        "plot_url": f"/get_plot/{os.path.basename(plot_path)}"
    })

@app.route("/get_aqi", methods=["POST"])
def get_aqi():
    city = request.form.get("city")
    weather_data = get_current_weather(city)

    if not weather_data:
        return jsonify({"error": "City not found"}), 400

    aqi_data = get_aqi_data(weather_data["lat"], weather_data["lon"])
    
    if not aqi_data:
        return jsonify({"error": "AQI data not found"}), 400

    return jsonify({
        "city": city,
        "country": weather_data["country"],
        "aqi": aqi_data.get("aqi_index", "N/A"),
        "pm25": aqi_data.get("pm2_5", "N/A"),
        "pm10": aqi_data.get("pm10", "N/A"),
        "co": aqi_data.get("co", "N/A"),
        "no2": aqi_data.get("no2", "N/A"),
        "so2": aqi_data.get("so2", "N/A"),
        "o3": aqi_data.get("o3", "N/A"),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/get_aqi_predictions", methods=["POST"])
def get_aqi_predictions():
    city = request.form.get("city")
    current_pm10 = request.form.get("pm10")
    current_o3 = request.form.get("o3")
    current_no2 = request.form.get("no2")

    if current_pm10 is None or current_o3 is None or current_no2 is None:
        return jsonify({"error": "Missing input values"}), 400  # Bad request

    try:
        current_pm10 = float(current_pm10)
        current_o3 = float(current_o3)
        current_no2 = float(current_no2)
    except ValueError:
        return jsonify({"error": "Invalid input values"}), 400  # Bad request

    # Read historical AQI dataset
    historical_data = read_historical_aqi_data()

    # Check if columns are present in the dataset
    required_columns = ["PM10 (ug/m3)", "Ozone (ug/m3)", "NO2 (ug/m3)"]
    for column in required_columns:
        if column not in historical_data.columns:
            return jsonify({"error": f"Missing required column: {column}"}), 400

    # Clean data by removing rows with missing values
    historical_data.dropna(subset=["PM10 (ug/m3)", "Ozone (ug/m3)", "NO2 (ug/m3)"], inplace=True)

    # Prepare regression data for PM10, Ozone, and NO2
    X_pm10, y_pm10 = prepare_pollutant_regression(historical_data, "PM10 (ug/m3)")
    X_o3, y_o3 = prepare_pollutant_regression(historical_data, "Ozone (ug/m3)")
    X_no2, y_no2 = prepare_pollutant_regression(historical_data, "NO2 (ug/m3)")

    # Train models for PM10, Ozone, and NO2
    pm10_model = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_pm10, y_pm10)
    o3_model = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_o3, y_o3)
    no2_model = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_no2, y_no2)

    # Predict future pollutant values
    future_pm10 = predict_future_pollutants(pm10_model, current_pm10)
    future_o3 = predict_future_pollutants(o3_model, current_o3)
    future_no2 = predict_future_pollutants(no2_model, current_no2)

    timezone = pytz.timezone("Asia/Kolkata")
    now = datetime.now(timezone)
    future_months = [(now + timedelta(days=30 * i)).strftime("%b %Y") for i in range(1, 13)]

    # Generate pollutant prediction plot
    plot_path = generate_pollutant_plot(city, future_months, future_pm10, future_o3, future_no2)

    return jsonify({
        "months": future_months,
        "pm10": list(map(lambda x: round(x, 1), future_pm10)),
        "o3": list(map(lambda x: round(x, 1), future_o3)),
        "no2": list(map(lambda x: round(x, 1), future_no2)),
        "plot_url": f"/get_plot/{os.path.basename(plot_path)}"
    })

#Generate weather prediction plots
def generate_plots(city, months, future_temp, future_humidity):
    plot_dir = "static"
    os.makedirs(plot_dir, exist_ok=True)

    plt.figure(figsize=(15, 5))

    # Line Graph
    plt.subplot(1, 3, 1)
    plt.plot(months, future_temp, marker='o', linestyle='-', color='r', label="Temp (°C)")
    plt.plot(months, future_humidity, marker='s', linestyle='--', color='b', label="Humidity (%)")
    plt.xticks(rotation=45)
    plt.title(f"Weather Predictions for {city}")
    plt.xlabel("Time (Months)")
    plt.ylabel("Values")
    plt.legend()

    # Bar Graph
    plt.subplot(1, 3, 2)
    plt.bar(months, future_temp, color='r', label="Temp (°C)", alpha=0.7)
    plt.bar(months, future_humidity, color='b', label="Humidity (%)", alpha=0.7)
    plt.xticks(rotation=45)
    plt.title("Bar Graph: Temperature vs Humidity")
    plt.legend()

    # Scatter Plot
    plt.subplot(1, 3, 3)
    plt.scatter(future_temp, future_humidity, color='g')
    plt.xlabel("Temperature (°C)")
    plt.ylabel("Humidity (%)")
    plt.title("Temp vs Humidity Scatter Plot")

    plot_path = f"{plot_dir}/{city}_weather_plot.png"
    plt.savefig(plot_path)
    plt.close()
    return plot_path

# Generate AQI Prediction Plot
def generate_pollutant_plot(city, months, future_pm10, future_o3, future_no2):
    plot_dir = "static"
    os.makedirs(plot_dir, exist_ok=True)

    plt.figure(figsize=(15, 5))

    # Line Graph
    plt.subplot(1, 3, 1)
    print(f"Future PM10: {future_pm10}")  # Debugging
    print(f"Future Ozone: {future_o3}")  # Debugging
    print(f"Future NO2: {future_no2}")  # Debugging
    plt.plot(months, future_pm10, marker='o', linestyle='-', color='red', label="PM10 (µg/m³)")
    plt.plot(months, future_o3, marker='s', linestyle='--', color='blue', label="O₃ (µg/m³)")
    plt.plot(months, future_no2, marker='^', linestyle='-.', color='green', label="NO₂ (µg/m³)")
    plt.xticks(rotation=45)
    plt.title(f"Pollutant Predictions for {city}")
    plt.xlabel("Time (Months)")
    plt.ylabel("Concentration (µg/m³)")
    plt.legend()

    # Bar Graph
    plt.subplot(1, 3, 2)
    bar_width = 0.2
    x = np.arange(len(months))
    plt.bar(x - bar_width, future_pm10, bar_width, color='red', label="PM10 (µg/m³)")
    plt.bar(x, future_o3, bar_width, color='blue', label="O₃ (µg/m³)")
    plt.bar(x + bar_width, future_no2, bar_width, color='green', label="NO₂ (µg/m³)")
    plt.xticks(x, months, rotation=45)
    plt.title("Bar Graph: Pollutant Concentrations")
    plt.legend()

    # Scatter Plot
    plt.subplot(1, 3, 3)
    plt.scatter(future_pm10, future_o3, color='purple', label="PM10 vs O₃", alpha=0.7)
    plt.scatter(future_pm10, future_no2, color='orange', label="PM10 vs NO₂", alpha=0.7)
    plt.xlabel("PM10 (µg/m³)")
    plt.ylabel("Pollutant Concentrations (µg/m³)")
    plt.title("Pollutant Scatter Plot")
    plt.legend()

    plot_path = f"{plot_dir}/{city}_pollutant_plot.png"
    plt.savefig(plot_path)
    plt.close()
    return plot_path

    
@app.route("/get_plot/<filename>")
def get_plot(filename):
    return send_file(f"static/{filename}", mimetype="image/png")

if __name__ == "__main__":
    app.run(debug=True)
