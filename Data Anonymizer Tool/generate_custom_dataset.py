import pandas as pd
import random
from faker import Faker

# Initialize Faker
fake = Faker()

# Number of rows
num_rows = 50

# Categories
categories = ["Pharma", "Chemicals", "Biotech", "Enzymes", "Nutrients"]

# Generate data
data = {
    "customer_id": [f"CUST{1000+i}" for i in range(num_rows)],
    "order_id": [f"ORD{2000+i}" for i in range(num_rows)],
    "category": [random.choice(categories) for _ in range(num_rows)],
    "quantity": [random.randint(1, 100) for _ in range(num_rows)],
    "price_per_unit": [round(random.uniform(50, 500), 2) for _ in range(num_rows)],
    "order_date": [fake.date_between(start_date="-1y", end_date="today") for _ in range(num_rows)],
    "delivery_date": [fake.date_between(start_date="today", end_date="+30d") for _ in range(num_rows)],
}

# Create DataFrame in required sequence
df = pd.DataFrame(data, columns=[
    "customer_id", "order_id", "category", 
    "quantity", "price_per_unit", 
    "order_date", "delivery_date"
])

# Save to CSV
df.to_csv("Custom_Dataset_50_Rows.csv", index=False)

print("✅ Dataset generated: Custom_Dataset_50_Rows.csv")
