import pandas as pd
import hashlib
from faker import Faker

fake = Faker()

def hash_value(val):
    if pd.isnull(val):
        return val
    return hashlib.sha256(str(val).encode()).hexdigest()[:10]

def fake_name(val):
    return fake.name()

def fake_email(val):
    return fake.email()

def fake_phone(val):
    return fake.phone_number()

def generalize_date(val):
    if pd.isnull(val):
        return val
    try:
        return pd.to_datetime(val).strftime("%Y-%m")  # keep only Year-Month
    except:
        return val

def redact(val):
    return "***"
