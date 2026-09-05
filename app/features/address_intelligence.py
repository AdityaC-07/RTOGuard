"""Indian delivery-address quality signals."""

import re
from typing import Dict

ADDRESS_INTELLIGENCE_FEATURE_NAMES = [
    "addr_has_unit_number", "addr_has_area_keyword", "addr_has_landmark",
    "addr_token_count", "addr_char_count", "addr_is_gibberish",
    "addr_consonant_cluster", "addr_all_caps_ratio",
]
AREA_WORDS = {"sector", "nagar", "vihar", "colony", "layout", "enclave", "apartments", "residency", "society", "phase", "extension", "cross", "main", "road", "street", "marg", "path"}
LANDMARK_WORDS = {"near", "opp", "opposite", "behind", "beside", "next", "above", "below", "adj", "adjacent"}


def address_intelligence_features(address: str) -> Dict[str, float]:
    value = str(address or "").strip()
    lower = value.lower()
    tokens = set(lower.split())
    token_count = len(lower.split())
    clusters = len(re.findall(r"[bcdfghjklmnpqrstvwxyz]{4,}", lower))
    return {
        "addr_has_unit_number": float(bool(re.search(r"\b\d+[a-zA-Z]?\b|\bfloor\s+\d+\b|\b[a-zA-Z]-\d+\b", lower))),
        "addr_has_area_keyword": float(bool(tokens & AREA_WORDS)),
        "addr_has_landmark": float(bool(tokens & LANDMARK_WORDS)),
        "addr_token_count": float(token_count),
        "addr_char_count": float(len(value)),
        "addr_is_gibberish": float(len(value) < 20 or token_count < 3),
        "addr_consonant_cluster": round(clusters / max(token_count, 1), 3),
        "addr_all_caps_ratio": round(sum(char.isupper() for char in value) / max(len(value), 1), 3),
    }