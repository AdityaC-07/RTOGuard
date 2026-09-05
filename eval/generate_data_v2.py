"""Adversarial Indian COD order generator for Phase 3 evaluation."""

import random
from typing import List

import pandas as pd

from eval.generate_data import COMPLETE_ADDRESS_TEMPLATES, LEGITIMATE_PINCODES, FRAUD_RING_PINCODES

FRAUD_ARCHETYPES: List[str] = [
    "classic_ring", "sophisticated", "probe_exploit", "geographic_cluster",
    "identity_rotator", "bulk_operator", "newcomer", "sleeper",
]
LEGIT_ARCHETYPES: List[str] = ["loyal_customer", "first_timer", "business_buyer"]


def _phone(rng: random.Random, prefix: str = "") -> str:
    return (prefix or str(rng.randint(6000, 9999))) + "".join(str(rng.randint(0, 9)) for _ in range(6))


def generate_synthetic_orders_v2(num_samples: int = 5000, rto_rate: float = 0.28, random_seed: int = 42) -> pd.DataFrame:
    rng = random.Random(random_seed)
    fraud_count = int(num_samples * rto_rate)
    shared_ring_devices = [f"DEV_RING_{i:03d}" for i in range(1, 16)]
    overlap_pincodes = ["560034", "400050", "110044", "600020"]
    shared_phones = [f"9{rng.randint(6, 9)}{rng.randint(10000000, 99999999)}" for _ in range(30)]
    rotator_pool = [f"DEV_ROT_{i:03d}" for i in range(1, 11)]
    universal_devices = shared_ring_devices + rotator_pool + [
        f"DEV_{archetype.upper()}_{i:03d}"
        for archetype in FRAUD_ARCHETYPES + LEGIT_ARCHETYPES
        for i in range(1, 11)
    ]

    def choose_device(archetype: str, index: int) -> str:
        own_pool = [f"DEV_{archetype.upper()}_{i:03d}" for i in range(1, 11)]
        if rng.random() < 0.90:
            return rng.choice(universal_devices)
        if archetype in {"identity_rotator", "bulk_operator"}:
            return rng.choice(rotator_pool + shared_ring_devices)
        return rng.choice(own_pool)

    def choose_phone(prefix: str = "") -> str:
        if rng.random() < 0.90:
            return rng.choice(shared_phones)
        if prefix == "98":
            return "98" + "".join(str(rng.randint(0, 9)) for _ in range(8))
        return _phone(rng, prefix)

    def choose_pincode() -> str:
        return rng.choice(overlap_pincodes) if rng.random() < 0.20 else rng.choice(LEGITIMATE_PINCODES)

    records = []
    for index in range(num_samples):
        is_rto = index < fraud_count
        archetype = (FRAUD_ARCHETYPES[index % len(FRAUD_ARCHETYPES)] if is_rto else LEGIT_ARCHETYPES[index % len(LEGIT_ARCHETYPES)])
        shared_device = choose_device(archetype, index)
        if archetype == "classic_ring":
            phone, pincode, address, value, device = choose_phone("9999"), rng.choice(FRAUD_RING_PINCODES), "Main Rd", rng.uniform(800, 2000), shared_device
        elif archetype == "sophisticated":
            phone, pincode, address, value, device = choose_phone(), choose_pincode(), rng.choice(COMPLETE_ADDRESS_TEMPLATES), rng.uniform(1200, 2500), shared_device
        elif archetype == "probe_exploit":
            phone, pincode, address, value, device = choose_phone(), choose_pincode(), rng.choice(COMPLETE_ADDRESS_TEMPLATES), 400.0 if index % 2 else 3500.0, shared_device
        elif archetype == "geographic_cluster":
            phone, pincode, address, value, device = choose_phone(), overlap_pincodes[index % len(overlap_pincodes)], rng.choice(COMPLETE_ADDRESS_TEMPLATES), rng.uniform(600, 1800), shared_device
        elif archetype == "identity_rotator":
            phone, pincode, address, value, device = choose_phone(), choose_pincode(), "14 MG Road", rng.uniform(1000, 2500), shared_device
        elif archetype == "bulk_operator":
            phone, pincode, address, value, device = choose_phone(), choose_pincode(), "Flat 12 Main Road", float(rng.randint(1200, 1899)), shared_device
        elif archetype == "newcomer":
            phone, pincode, address, value, device = choose_phone(), choose_pincode(), "House 8 Sector 4", rng.uniform(2501, 5000), shared_device
        elif archetype == "sleeper":
            phone, pincode, address, value, device = choose_phone(), choose_pincode(), rng.choice(COMPLETE_ADDRESS_TEMPLATES), rng.uniform(1800, 4000), shared_device
        elif archetype == "loyal_customer":
            phone, pincode, address, value, device = choose_phone("98"), choose_pincode(), rng.choice(COMPLETE_ADDRESS_TEMPLATES), rng.uniform(300, 2500), shared_device
        elif archetype == "first_timer":
            phone, pincode, address, value, device = choose_phone(), choose_pincode(), "Plot 4", rng.uniform(200, 900), shared_device
        else:
            phone, pincode, address, value, device = choose_phone(), choose_pincode(), rng.choice(COMPLETE_ADDRESS_TEMPLATES), rng.uniform(2500, 10000), shared_device
        records.append({
            "order_id": f"ORD_{index:06d}", "phone": phone, "pincode": pincode,
            "address": address, "order_value": round(value, 2), "device_id": device,
            "archetype": archetype, "is_rto": int(is_rto),
        })
    return pd.DataFrame(records).sample(frac=1, random_state=random_seed).reset_index(drop=True)


if __name__ == "__main__":
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score

    data = generate_synthetic_orders_v2(num_samples=5000, random_seed=42)
    for feature in ("device_id", "phone"):
        encoded = pd.get_dummies(data[[feature]])
        scores = cross_val_score(
            RandomForestClassifier(n_estimators=10, random_state=0),
            encoded, data["is_rto"], cv=3, scoring="f1",
        )
        print(f"Leakage check - {feature} alone -> F1 {scores.mean():.3f}")
        assert scores.mean() < 0.70, f"LEAKAGE: {feature} alone scores {scores.mean():.3f}"
    print("Leakage checks passed.")
    print(data.groupby(["archetype", "is_rto"]).size())