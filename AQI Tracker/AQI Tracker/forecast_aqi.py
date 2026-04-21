import pandas as pd

# Path to your AQI CSV file
file_path = r"C:\Users\Avadhoot\Desktop\SEM 6 Project\aqi_cleaned.csv"
cleaned_file_path = r"C:\Users\Avadhoot\Desktop\SEM 6 Project\aqi.csv"

# Load CSV file
try:
    df = pd.read_csv(file_path)
    print("✅ CSV file loaded successfully!")
except Exception as e:
    print(f"❌ Error loading CSV: {e}")
    exit()

# Show first few rows
print("\n🔹 First few rows BEFORE cleaning:")
print(df.head())

# Trim spaces from column names
df.columns = df.columns.str.strip()

# Remove duplicate rows
df = df.drop_duplicates()

# Check if required columns exist
pollutants = ["PM2.5 (ug/m3)", "PM10 (ug/m3)", "NO2 (ug/m3)", "CO (mg/m3)", "SO2 (ug/m3)", "Ozone (ug/m3)"]
missing_columns = [col for col in pollutants if col not in df.columns]

if missing_columns:
    print(f"❌ Missing columns in CSV: {missing_columns}")
else:
    print("✅ All required columns are present!")

# Ensure numeric data
for col in pollutants:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')  # Convert to numbers, set invalid values to NaN

# **🔹 Fix: Instead of dropping NaNs, fill them with the column mean**
df = df.fillna(df.mean(numeric_only=True))

# Check if the dataset is still empty
if df.shape[0] == 0:
    print("❌ Error: No valid data left after cleaning! Check your CSV file.")
    exit()

# Save cleaned CSV
df.to_csv(cleaned_file_path, index=False)
print(f"\n✅ Cleaned CSV saved at: {cleaned_file_path}")
print("\n🔹 First few rows AFTER cleaning:")
print(df.head())

# Final dataset check
print(f"\n📊 Final dataset shape: {df.shape}")