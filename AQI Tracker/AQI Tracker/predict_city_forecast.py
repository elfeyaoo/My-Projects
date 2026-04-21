import pandas as pd
from prophet import Prophet
import matplotlib.pyplot as plt

# Function to predict future values
def predict_future(data, column, periods=730):  # 2 years (365*2)
    model = Prophet()
    model.fit(data.rename(columns={"Date": "ds", column: "y"}))
    future = model.make_future_dataframe(periods=periods, freq="D")
    forecast = model.predict(future)
    return forecast

# Load forecasted AQI and Weather data
aqi_df = pd.read_csv("aqi_forecast.csv")
weather_df = pd.read_csv("weather_forecast.csv")

# Convert Date columns to datetime
aqi_df["ds"] = pd.to_datetime(aqi_df["ds"])
weather_df["ds"] = pd.to_datetime(weather_df["ds"])

# Take city input
city = input("Enter city name: ").strip()

# Filter AQI data for the given city if available
if "City" in aqi_df.columns:
    aqi_city_df = aqi_df[aqi_df["City"] == city]
    if aqi_city_df.empty:
        print("City not found in AQI dataset.")
    else:
        aqi_forecast = predict_future(aqi_city_df, "yhat")
        plt.figure(figsize=(10, 5))
        plt.plot(aqi_forecast["ds"], aqi_forecast["yhat"], label="Predicted AQI")
        plt.fill_between(aqi_forecast["ds"], aqi_forecast["yhat_lower"], aqi_forecast["yhat_upper"], alpha=0.2)
        plt.xlabel("Date")
        plt.ylabel("AQI")
        plt.title(f"AQI Forecast for {city} (2025-2026)")
        plt.legend()
        plt.show()
        print(aqi_forecast[["ds", "yhat"]].tail(10))

# Filter Weather data for the given city if available
if "City" in weather_df.columns:
    weather_city_df = weather_df[weather_df["City"] == city]
    if weather_city_df.empty:
        print("City not found in Weather dataset.")
    else:
        weather_forecast = predict_future(weather_city_df, "yhat")
        plt.figure(figsize=(10, 5))
        plt.plot(weather_forecast["ds"], weather_forecast["yhat"], label="Predicted Temperature")
        plt.fill_between(weather_forecast["ds"], weather_forecast["yhat_lower"], weather_forecast["yhat_upper"], alpha=0.2)
        plt.xlabel("Date")
        plt.ylabel("Temperature (C)")
        plt.title(f"Weather Forecast for {city} (2025-2026)")
        plt.legend()
        plt.show()
        print(weather_forecast[["ds", "yhat"]].tail(10))
