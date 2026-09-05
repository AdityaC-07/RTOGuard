"""Synthetic order generator for RTOGuard evaluation.
Produces realistic Indian COD order data with embedded fraud patterns
based on CARE-GNN camouflage theory: ring signals via shared pincodes,
device IDs, and address tokens."""

import numpy as np
import pandas as pd
import hashlib
import random
import string
from typing import List, Tuple

FRAUD_RING_PINCODES: List[str] = ["110001", "400001", "500001", "600001", "700001", "560001", "380001", "302001"]
FRAUD_RING_PHONE_PREFIXES: List[str] = ["9999", "8888", "7777", "6666", "9876"]
LEGITIMATE_PINCODES: List[str] = ["110005", "110006", "400050", "400051", "500010", "500011", "600010", "600011", "700010", "700011", "560010", "560011", "380010", "380011", "302010", "302011", "110025", "400025", "500025", "600025"]
INCOMPLETE_ADDRESS_TEMPLATES: List[str] = ["Main Rd", "XYZ Lane", "St 5", "Apt", "Sec 12", "Near Metro", "Plot 44", "Zone A", "Block B", "Area C"]
COMPLETE_ADDRESS_TEMPLATES: List[str] = [
    "Flat 4B, 2nd Floor, Sunrise Apartments, Koramangala, Bangalore",
    "House No. 123, 1st Cross, Indiranagar, Bangalore",
    "Suite 302, Tech Park, Whitefield, Bangalore",
    "Flat 305, Emerald Court, Malviya Nagar, New Delhi",
    "House 45, Pocket A, Vasant Kunj, New Delhi",
    "Office 12, Business Hub, Powai, Mumbai",
    "Flat 7C, Palm Springs, Borivali, Mumbai",
    "House 34, Brigade Road, Bangalore",
    "Apartment 201, Crescent Heights, Gurgaon",
    "Flat 15, Maple Residency, Pune"
]


def generate_synthetic_orders(
    num_samples: int = 1000,
    rto_rate: float = 0.28,
    random_seed: int = 42
) -> pd.DataFrame:
    np.random.seed(random_seed)
    random.seed(random_seed)

    fraud_count = int(num_samples * rto_rate)
    legit_count = num_samples - fraud_count

    fraud_records = []
    for i in range(fraud_count):
        # 60% use fraud ring prefixes, 40% use random (camouflage)
        if random.random() < 0.6:
            phone_prefix = random.choice(FRAUD_RING_PHONE_PREFIXES)
        else:
            phone_prefix = str(random.randint(6000, 9999))
        phone = phone_prefix + "".join([str(random.randint(0, 9)) for _ in range(6)])

        # 70% use fraud pincodes, 30% use legitimate (relation camouflage)
        if random.random() < 0.7:
            pincode = random.choice(FRAUD_RING_PINCODES)
        else:
            pincode = random.choice(LEGITIMATE_PINCODES)

        # 80% use incomplete address, 20% use complete (feature camouflage)
        if random.random() < 0.8:
            address = random.choice(INCOMPLETE_ADDRESS_TEMPLATES)
        else:
            address = random.choice(COMPLETE_ADDRESS_TEMPLATES)

        # 50% share a device ID from a ring, 50% unique
        if random.random() < 0.5:
            device_id = f"DEV_RING_{chr(65 + random.randint(0, 4))}"
        else:
            device_id = f"DEV_{hashlib.md5(str(random.random()).encode()).hexdigest()[:8].upper()}"

        order_value = float(np.random.uniform(800, 3000))

        fraud_records.append({
            "order_id": f"ORD_{str(i).zfill(6)}",
            "phone": phone,
            "pincode": pincode,
            "address": address,
            "order_value": round(order_value, 2),
            "device_id": device_id,
            "is_rto": 1,
            "pincode_is_fraud_zone": 1 if pincode in FRAUD_RING_PINCODES else 0,
            "phone_is_ring_prefix": 1 if phone[:4] in FRAUD_RING_PHONE_PREFIXES else 0
        })

    legit_records = []
    for i in range(legit_count):
        phone = str(random.randint(6, 9)) + "".join([str(random.randint(0, 9)) for _ in range(9)])
        pincode = random.choice(LEGITIMATE_PINCODES)
        address = random.choice(COMPLETE_ADDRESS_TEMPLATES)
        device_id = f"DEV_{hashlib.md5(str(random.random()).encode()).hexdigest()[:8].upper()}"
        order_value = float(np.random.uniform(200, 4000))

        legit_records.append({
            "order_id": f"ORD_{str(fraud_count + i).zfill(6)}",
            "phone": phone,
            "pincode": pincode,
            "address": address,
            "order_value": round(order_value, 2),
            "device_id": device_id,
            "is_rto": 0,
            "pincode_is_fraud_zone": 0,
            "phone_is_ring_prefix": 0
        })

    all_records = fraud_records + legit_records
    df = pd.DataFrame(all_records)
    df = df.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = generate_synthetic_orders(1000)
    print(f"Total orders: {len(df)}")
    print(f"RTO rate: {df['is_rto'].mean():.2%}")
    print(f"Ring phone prefix fraud rate: {df[df['phone_is_ring_prefix']==1]['is_rto'].mean():.2%}")
    print(df.head(5).to_string())
