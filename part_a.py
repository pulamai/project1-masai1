import os
import sqlite3
import pandas as pd
import numpy as np

def run_part_a():
    os.makedirs("data/clean", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("sql", exist_ok=True)

    # Load raw data
    cust_raw = pd.read_csv("data/raw/customers.csv")
    prod_raw = pd.read_csv("data/raw/products.csv")
    orders_raw = pd.read_csv("data/raw/orders.csv")
    tickets_raw = pd.read_csv("data/raw/tickets.csv", keep_default_na=False)

    print("--- 2. Audit Raw Data ---")
    print(f"Orders shape: {orders_raw.shape}, Exact duplicates: {orders_raw.duplicated().sum()}")
    print(f"Pending rows: {(orders_raw['status'] == 'pending').sum()}")
    print(f"Distinct order_ids: {orders_raw['order_id'].nunique()}")

    # --- 3. Clean Customers ---
    df_c = cust_raw.copy()
    df_c['city'] = df_c['city'].astype(str).str.strip().str.title()

    gender_map = {
        'male': 'male', 'Male': 'male', 'M': 'male', 'm': 'male', 'MALE': 'male',
        'female': 'female', 'Female': 'female', 'F': 'female', 'f': 'female', 'FEMALE': 'female'
    }
    df_c['gender'] = df_c['gender'].map(gender_map).fillna('unknown')

    df_c['age'] = pd.to_numeric(df_c['age'], errors='coerce')
    df_c.loc[(df_c['age'] < 10) | (df_c['age'] > 100), 'age'] = np.nan
    df_c['age'] = df_c['age'].fillna(df_c.groupby('city')['age'].transform('median'))
    df_c['signup_date'] = pd.to_datetime(df_c['signup_date'])

    # --- 4. Clean Orders ---
    df_o = orders_raw.copy()
    df_o['order_ts'] = pd.to_datetime(df_o['order_ts'])
    df_o = df_o.drop_duplicates()

    # Keep latest order_ts per order_id
    df_o = df_o.sort_values('order_ts').drop_duplicates(subset=['order_id'], keep='last')

    df_o['order_amount'] = pd.to_numeric(df_o['order_amount'], errors='coerce')

    # Merge product price to fix missing/unparseable amounts
    df_o = df_o.merge(prod_raw[['product_id', 'price_inr']], on='product_id', how='left')
    missing_amt_mask = df_o['order_amount'].isna()
    df_o.loc[missing_amt_mask, 'order_amount'] = round(
        df_o.loc[missing_amt_mask, 'price_inr'] * df_o.loc[missing_amt_mask, 'quantity'] * (1 - df_o.loc[missing_amt_mask, 'discount_pct'] / 100), 2
    )

    df_o['delivery_minutes'] = pd.to_numeric(df_o['delivery_minutes'], errors='coerce')
    df_o.loc[df_o['delivery_minutes'] < 0, 'delivery_minutes'] = np.nan

    # Impute completed delivery minutes by product category median
    df_o = df_o.merge(prod_raw[['product_id', 'category']], on='product_id', how='left')
    completed_mask = df_o['status'] == 'completed'
    cat_medians = df_o[completed_mask].groupby('category')['delivery_minutes'].transform('median')
    df_o.loc[completed_mask & df_o['delivery_minutes'].isna(), 'delivery_minutes'] = cat_medians[completed_mask & df_o['delivery_minutes'].isna()]

    df_o = df_o.drop(columns=['price_inr', 'category'])

    # --- 5. Store & Validate ---
    df_c.to_csv("data/clean/customers.csv", index=False)
    prod_raw.to_csv("data/clean/products.csv", index=False)
    df_o.to_csv("data/clean/orders.csv", index=False)

    conn = sqlite3.connect("data/instamart.db")
    df_c.to_sql("customers", conn, if_exists="replace", index=False)
    prod_raw.to_sql("products", conn, if_exists="replace", index=False)
    df_o.to_sql("orders", conn, if_exists="replace", index=False)
    conn.close()

    # Validation check
    completed_spend = df_o[df_o['status'] == 'completed']['order_amount'].sum()
    assert len(df_o) == 12309, f"Expected 12309 rows, got {len(df_o)}"
    assert round(completed_spend, 2) == 2998668.80, f"Revenue mismatch: {completed_spend}"
    print("ALL CHECKPOINTS PASSED")

if __name__ == "__main__":
    run_part_a()
