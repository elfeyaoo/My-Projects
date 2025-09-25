# anonymizer.py
import pandas as pd
import hashlib
import random
from faker import Faker

fake = Faker()

def hash_value(val):
    if pd.isnull(val):
        return val
    return hashlib.sha256(str(val).encode()).hexdigest()[:12]

def perturb_price(x, pct=0.05):
    try:
        v = float(x)
        noise = v * pct * (random.random() * 2 - 1)  # +/- pct
        return round(v + noise, 2)
    except:
        return x

def generalize_date_to_month(val):
    try:
        return pd.to_datetime(val).strftime("%Y-%m")
    except:
        return val

def redact(val):
    return "***"

def anonymize_dataframe(df, mode="field-wise", percentage=50):
    """
    mode:
      - 'all-rows' : randomly pick percentage of rows and anonymize key fields in those rows
      - 'month-wise': group by order_date month and anonymize rows within month by percentage
      - 'field-wise': anonymize predefined columns for entire dataset
    """
    df = df.copy()
    if mode == "all-rows":
        frac = max(0.01, min(1.0, percentage / 100.0))
        idx = df.sample(frac=frac, random_state=42).index
        df.loc[idx, "customer_id"] = df.loc[idx, "customer_id"].apply(hash_value)
        df.loc[idx, "order_id"] = df.loc[idx, "order_id"].apply(hash_value)
        df.loc[idx, "price_per_unit"] = df.loc[idx, "price_per_unit"].apply(lambda x: perturb_price(x, pct=0.05))
    elif mode == "month-wise":
        if "order_date" in df.columns:
            df["order_date_parsed"] = pd.to_datetime(df["order_date"], errors="coerce")
            frac = max(0.01, min(1.0, percentage / 100.0))
            for _, g in df.groupby(df["order_date_parsed"].dt.to_period("M")):
                if g.empty: continue
                rows = g.sample(frac=frac, random_state=42).index
                df.loc[rows, "customer_id"] = df.loc[rows, "customer_id"].apply(hash_value)
            df.drop(columns=["order_date_parsed"], inplace=True)
    else:  # field-wise default
        if "customer_id" in df.columns:
            df["customer_id"] = df["customer_id"].apply(hash_value)
        if "order_id" in df.columns:
            df["order_id"] = df["order_id"].apply(hash_value)
        if "category" in df.columns:
            # generalize categories to generic labels
            df["category"] = df["category"].apply(lambda x: "Category_" + str(abs(hash(str(x))) % 100))
        if "price_per_unit" in df.columns:
            df["price_per_unit"] = df["price_per_unit"].apply(lambda x: perturb_price(x, pct=0.03))
        if "order_date" in df.columns:
            df["order_date"] = df["order_date"].apply(generalize_date_to_month)
        if "delivery_date" in df.columns:
            df["delivery_date"] = df["delivery_date"].apply(generalize_date_to_month)
    return df
