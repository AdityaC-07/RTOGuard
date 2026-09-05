"""Cheap time-of-order features."""

from datetime import datetime
from typing import Dict

TIME_FEATURE_NAMES = [
    "order_hour", "order_is_late_night", "order_is_business_hours",
    "order_day_of_week", "order_is_weekend",
]


def time_features(scored_at: datetime = None) -> Dict[str, float]:
    current = scored_at or datetime.now()
    return {
        "order_hour": float(current.hour),
        "order_is_late_night": float(1 <= current.hour <= 4),
        "order_is_business_hours": float(9 <= current.hour <= 18),
        "order_day_of_week": float(current.weekday()),
        "order_is_weekend": float(current.weekday() >= 5),
    }