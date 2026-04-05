import os
import random
import pandas as pd
from datetime import datetime, timedelta

def generate_mock_dataset(num_suppliers: int = 50, num_customers: int = 200, num_transactions: int = 1000):
    supplier_ids = [f"S_{i:04d}" for i in range(1, num_suppliers + 1)]
    customer_ids = [f"C_{i:04d}" for i in range(1, num_customers + 1)]
    
    # Introduce some "fraudulent" suppliers
    fraud_suppliers = set(random.sample(supplier_ids, max(1, int(num_suppliers * 0.1))))
    
    transactions = []
    base_date = datetime.now() - timedelta(days=90)
    
    for _ in range(num_transactions):
        s_id = random.choice(supplier_ids)
        c_id = random.choice(customer_ids)
        amount = round(random.uniform(10.0, 5000.0), 2)
        
        # Fraud features: higher amounts, specific times, etc.
        is_fraud = s_id in fraud_suppliers and random.random() < 0.6
        if is_fraud:
            amount = round(random.uniform(5000.0, 25000.0), 2)
            
        txn_date = base_date + timedelta(days=random.randint(0, 90), hours=random.randint(0, 23))
        
        transactions.append({
            "transaction_id": f"TXN_{len(transactions):06d}",
            "supplier_id": s_id,
            "customer_id": c_id,
            "amount": amount,
            "timestamp": txn_date.isoformat(),
            "is_suspicious": 1 if is_fraud else 0, # simulated label
            "feature_1": random.uniform(0, 1), # mock ml features
            "feature_2": random.uniform(-1, 1)
        })
        
    df = pd.DataFrame(transactions)
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    out_path = os.path.join(os.path.dirname(__file__), "mock_dataset.csv")
    df.to_csv(out_path, index=False)
    print(f"Generated mock dataset with {len(df)} rows at {out_path}")

if __name__ == "__main__":
    generate_mock_dataset()
