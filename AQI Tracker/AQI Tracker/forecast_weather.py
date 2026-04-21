import pandas as pd
from prophet import Prophet
import matplotlib.pyplot as plt

# Load the weather dataset
weather_df = pd.read_csv("weather.csv")

# Strip spaces from column names (if any)
weather_df.columns = weather_df.columns.str.strip()

# Rename "Formatted Date" to "Date" for consistency
weather_df.rename(columns={"Formatted Date": "Date"}, inplace=True)

# Convert Date column to datetime format (force UTC and remove timezone)
weather_df["Date"] = pd.to_datetime(weather_df["Date"], errors="coerce", utc=True).dt.tz_localize(None)

# If Date conversion failed, assume consecutive daily records
if weather_df["Date"].isna().sum() > 0:
    weather_df["Date"] = pd.date_range(start="2023-01-01", periods=len(weather_df), freq="D")

# Sort by Date to maintain proper order
weather_df = weather_df.sort_values(by="Date")

# Select the temperature column for forecasting
weather_forecast_col = "Temperature (C)"

# **Fill missing temperature values using interpolation**
weather_df[weather_forecast_col] = weather_df[weather_forecast_col].interpolate(method="linear")

# Drop remaining NaN values if any
weather_df = weather_df.dropna(subset=[weather_forecast_col])

# Ensure at least 2 data points exist
if weather_df.shape[0] < 2:
    raise ValueError("Not enough valid data points after filling missing values.")

# Prepare data for Prophet
weather_prophet_df = weather_df[["Date", weather_forecast_col]].rename(columns={"Date": "ds", weather_forecast_col: "y"})

# Initialize and fit Prophet model
weather_model = Prophet()
weather_model.fit(weather_prophet_df)

# Create future dataframe (predict next 30 days)
future_weather = weather_model.make_future_dataframe(periods=30, freq="D")

# Predict future weather values
weather_forecast = weather_model.predict(future_weather)

# Plot results
fig = weather_model.plot(weather_forecast)
plt.show()

# Save forecast to CSV
weather_forecast.to_csv("weather_forecast.csv", index=False)
print("Weather Forecast saved to weather_forecast.csv")
