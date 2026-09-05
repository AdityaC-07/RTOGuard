"""Local phone-shape signals; no carrier lookup is required."""

import math
import re
from typing import Dict

PHONE_FEATURE_NAMES = [
    "phone_is_known_operator", "phone_is_voip_pattern", "phone_digit_entropy",
    "phone_sequential_digits", "phone_repeated_digits",
]
KNOWN_PREFIXES = {"9820", "9819", "9811", "9810", "9876", "9999"}


def _entropy(value: str) -> float:
    counts = {digit: value.count(digit) for digit in set(value)}
    length = max(len(value), 1)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def phone_features(phone: str) -> Dict[str, float]:
    digits = re.sub(r"\D", "", str(phone or ""))[-10:]
    if len(digits) != 10:
        return {name: 0.0 for name in PHONE_FEATURE_NAMES}
    sequential = any(
        digits[index:index + 4] in ("0123", "1234", "2345", "3456", "4567", "5678", "6789", "9876", "8765", "7654", "6543", "5432", "4321", "3210")
        for index in range(7)
    )
    repeated = len(set(digits)) <= 2 or any(digits[index:index + 2] * 2 in digits for index in range(9))
    descending = any(digits[index:index + 4] in ("9876", "8765", "7654", "6543", "5432", "4321", "3210") for index in range(7))
    entropy = _entropy(digits) - (1.0 if descending else (0.5 if sequential else 0.0))
    return {
        "phone_is_known_operator": float(digits[:4] in KNOWN_PREFIXES),
        "phone_is_voip_pattern": float(digits[:4] in {"0120", "0124", "0172"}),
        "phone_digit_entropy": round(max(0.0, entropy), 4),
        "phone_sequential_digits": float(sequential),
        "phone_repeated_digits": float(repeated),
    }