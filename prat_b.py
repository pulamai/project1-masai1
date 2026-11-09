%%writefile part_b.py
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, classification_report, confusion_matrix
import joblib
import os

def run_part_b():
    os.makedirs("outputs", exist_ok=True)

    orders = pd.read_csv("data/clean/orders.csv")
    customers = pd.read_csv("data/clean/customers.csv")
    products = pd.read_csv("data/clean/products.csv")

    orders['order_ts'] = pd.to_datetime(orders['order_ts'])
    comp_orders = orders[orders['status'] == 'completed'].copy()

    # 1. RFM Table
    snapshot = pd.to_datetime("2025-10-01 00:00:00")
    rfm = comp_orders.groupby('customer_id').agg(
        recency=('order_ts', lambda x: (snapshot - x.max()).days),
        frequency=('order_id', 'count'),
        monetary=('order_amount', 'sum')
    ).reset_index()

    # 2. K-means Clustering (K=4 chosen based on silhouette and business interpretability)
    scaler = StandardScaler()
    rfm_scaled = scaler.fit_transform(rfm[['recency', 'frequency', 'monetary']])

    kmeans = KMeans(n_clusters=4, n_init=10, random_state=42)
    rfm['cluster'] = kmeans.fit_predict(rfm_scaled)

    # Label segments
    cluster_means = rfm.groupby('cluster')['monetary'].mean().reset_index()
    premium_cluster = cluster_means.loc[cluster_means['monetary'].idxmax(), 'cluster']

    rfm['segment_id'] = rfm['cluster']
    rfm['is_premium'] = rfm['cluster'] == premium_cluster
    rfm['segment_name'] = rfm['cluster'].map({
        0: 'Frequent Shoppers', 1: 'High-Value VIP', 2: 'Occasional Buyers', 3: 'At-Risk Lapsed'
    })

    # PCA
    pca = PCA(n_components=2, random_state=42)
    pca.fit(rfm_scaled)

    rfm[['customer_id', 'recency', 'frequency', 'monetary', 'segment_id', 'segment_name', 'is_premium']]\
        .to_csv("outputs/customer_segments.csv", index=False)

    # 4. Lapse Problem Setup
    cutoff = pd.to_datetime("2025-09-01 00:00:00")
    pre_orders = orders[orders['order_ts'] < cutoff]

    cohort_cids = pre_orders[pre_orders['status'] == 'completed']['customer_id'].unique()
    cohort = customers[customers['customer_id'].isin(cohort_cids)].copy()

    sept_orders = orders[(orders['order_ts'] >= cutoff) & (orders['order_ts'] < pd.to_datetime("2025-10-01"))]
    active_sept = set(sept_orders[sept_orders['status'] == 'completed']['customer_id'])

    cohort['lapsed'] = cohort['customer_id'].apply(lambda x: 0 if x in active_sept else 1)

    # Features
    feat = pre_orders.groupby('customer_id').agg(
        recency=('order_ts', lambda x: (cutoff - x.max()).days),
        frequency=('order_id', 'count'),
        monetary=('order_amount', lambda x: x[pre_orders['status'] == 'completed'].sum()),
        avg_discount=('discount_pct', 'mean'),
        avg_delivery=('delivery_minutes', 'mean')
    ).reset_index()

    # Cancellation rate
    cancel_counts = pre_orders[pre_orders['status'].isin(['completed', 'cancelled'])].groupby(['customer_id', 'status']).size().unstack(fill_value=0)
    if 'cancelled' in cancel_counts.columns and 'completed' in cancel_counts.columns:
        cancel_counts['cancel_rate'] = cancel_counts['cancelled'] / (cancel_counts['cancelled'] + cancel_counts['completed'])
    else:
        cancel_counts['cancel_rate'] = 0.0
    feat = feat.merge(cancel_counts[['cancel_rate']].reset_index(), on='customer_id', how='left')

    # Favourite category
    prod_cat = products.merge(pre_orders, on='product_id')
    fav_cat = prod_cat.groupby(['customer_id', 'category']).size().reset_index(name='count')
    fav_cat = fav_cat.sort_values(['customer_id', 'count'], ascending=[True, False]).drop_duplicates(subset=['customer_id'])
    feat = feat.merge(fav_cat[['customer_id', 'category']].rename(columns={'category': 'fav_category'}), on='customer_id', how='left')

    merged_data = cohort.merge(feat, on='customer_id', how='left').fillna({'frequency': 0, 'monetary': 0, 'cancel_rate': 0})
    merged_data['tenure'] = (cutoff - pd.to_datetime(merged_data['signup_date'])).dt.days

    X = merged_data[['recency', 'frequency', 'monetary', 'avg_discount', 'avg_delivery', 'cancel_rate', 'city', 'gender', 'fav_category', 'age', 'tenure']]
    y = merged_data['lapsed']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    # Preprocessing with Pipeline or Manual mapping without leakage
    numeric_cols = ['recency', 'frequency', 'monetary', 'avg_discount', 'avg_delivery', 'cancel_rate', 'age', 'tenure']
    categorical_cols = ['city', 'gender', 'fav_category']

    num_scaler = StandardScaler()
    X_train_num = num_scaler.fit_transform(X_train[numeric_cols].fillna(0))
    X_test_num = num_scaler.transform(X_test[numeric_cols].fillna(0))

    encoder = OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore')
    X_train_cat = encoder.fit_transform(X_train[categorical_cols].fillna('unknown'))
    X_test_cat = encoder.transform(X_test[categorical_cols].fillna('unknown'))

    X_train_proc = np.hstack([X_train_num, X_train_cat])
    X_test_proc = np.hstack([X_test_num, X_test_cat])

    # Train Random Forest
    rf = RandomForestClassifier(n_estimators=100, max_depth=8, min_samples_leaf=10, random_state=42)
    rf.fit(X_train_proc, y_train)

    joblib.dump((rf, num_scaler, encoder), "outputs/lapse_model.joblib")

    # Retention list for premium customers
    segments = pd.read_csv("outputs/customer_segments.csv")
    test_cids = X_test.assign(lapsed_true=y_test)['customer_id'] if 'customer_id' in X_test else X_test.index
    # Generate predictions on test set
    preds = rf.predict_proba(X_test_proc)[:, 1]
    test_res = pd.DataFrame({'customer_id': X_test['customer_id'].values if 'customer_id' in X_test else X_test.index, 'lapse_probability': preds, 'actually_lapsed': y_test.values})

    premium_test = test_res.merge(segments[segments['is_premium'] == True], on='customer_id')
    premium_test.sort_values('lapse_probability', ascending=False).head(10)[['customer_id', 'lapse_probability', 'actually_lapsed']]\
        .to_csv("outputs/retention_list.csv", index=False)

    print("Part B completed successfully.")

if __name__ == "__main__":
    run_part_b()
