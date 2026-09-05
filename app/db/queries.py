"""Phase 2 history-signal queries over the orders table.

All functions degrade to neutral defaults (0 / 0.0) when the DB is empty,
the table is missing, or identifiers are unknown — the day-1 cold-start
guarantee. Nothing here may raise to callers.
"""

import logging
import re
import unicodedata
from typing import Any, Dict

from app.db.connection import get_connection

logger = logging.getLogger("rtoguard.db.queries")

_UNKNOWN_DEVICES = {"", "UNKNOWN", "NONE", "NULL"}


def resolve_device_key(device_id: Any, phone: Any = "") -> str:
    """Stable per-actor key. Falls back to the phone's last 10 digits when
    no real device_id is supplied (dashboard presets omit device_id), so
    history still accumulates per customer instead of one giant UNKNOWN
    bucket that would false-positive on rotation."""
    dev = str(device_id or "").strip()
    if dev and dev.upper() not in _UNKNOWN_DEVICES:
        return dev
    digits = re.sub(r"\D", "", str(phone or ""))
    if len(digits) >= 10:
        return f"PHONE_{digits[-10:]}"
    return ""


def canonicalise_address(address: Any) -> str:
    """Reduce spelling variants to a comparable token.

    "Flat 4B, 2nd Floor, M.G. Road!" -> "flat 4b 2nd floor mg road"
    "14, M.G. Road" and "Plot 14 MG Road" share the token "14 mg road".
    """
    if address is None:
        return ""
    s = str(address).lower()
    try:
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
    except Exception:
        pass
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace(" rd ", " road ").replace(" st ", " street ")
    s = s.replace(" apt ", " apartment ").replace(" flr ", " floor ")
    # Collapse single-letter runs ("m g road" from "M.G. Road" -> "mg road")
    # so dotted abbreviations match their plain forms.
    tokens = s.split()
    merged: list = []
    i = 0
    while i < len(tokens):
        if len(tokens[i]) == 1 and tokens[i].isalpha():
            j = i
            while j < len(tokens) and len(tokens[j]) == 1 and tokens[j].isalpha():
                j += 1
            merged.append("".join(tokens[i:j]))
            i = j
        else:
            merged.append(tokens[i])
            i += 1
    return " ".join(merged)


def device_history_features(
    device_id: Any, phone: Any = "", db_path: Any = None
) -> Dict[str, float]:
    neutral = {
        "device_unique_phones_90d": 0.0,
        "device_total_orders_90d": 0.0,
        "device_flag_rate_90d": 0.0,
        "device_is_high_rotation": 0.0,
    }
    key = resolve_device_key(device_id, phone)
    if not key:
        return neutral
    try:
        conn = get_connection(db_path)
        try:
            row = conn.execute(
                """SELECT COUNT(DISTINCT phone) AS unique_phones,
                          COUNT(DISTINCT pincode) AS unique_pincodes,
                          COUNT(*) AS total_orders,
                          AVG(order_value) AS avg_value,
                          SUM(CASE WHEN decision = 'FLAG_FOR_REVIEW' THEN 1 ELSE 0 END) AS prev_flags
                   FROM orders
                   WHERE device_id = ?
                     AND scored_at >= datetime('now', '-90 days')""",
                (key,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return neutral
        unique_phones = int(row["unique_phones"] or 0)
        total_orders = int(row["total_orders"] or 0)
        prev_flags = int(row["prev_flags"] or 0)
        return {
            "device_unique_phones_90d": float(unique_phones),
            "device_total_orders_90d": float(total_orders),
            "device_flag_rate_90d": float(prev_flags / max(total_orders, 1)),
            "device_is_high_rotation": float(1 if unique_phones > 5 else 0),
        }
    except Exception as e:
        logger.warning(f"device_history_features failed: {e}")
        return neutral


def address_cluster_score(address: Any, db_path: Any = None) -> Dict[str, float]:
    neutral = {
        "address_seen_before": 0.0,
        "address_prior_flag_count": 0.0,
        "address_flag_rate": 0.0,
    }
    canonical = canonicalise_address(address)
    if not canonical:
        return neutral
    try:
        conn = get_connection(db_path)
        try:
            row = conn.execute(
                """SELECT COUNT(*) AS c,
                          SUM(CASE WHEN decision != 'APPROVE' THEN 1 ELSE 0 END) AS flagged
                   FROM orders
                   WHERE address_token LIKE ?
                     AND scored_at >= datetime('now', '-180 days')""",
                (canonical[:20] + "%",),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return neutral
        total = int(row["c"] or 0)
        flagged = int(row["flagged"] or 0)
        return {
            "address_seen_before": float(1 if total > 0 else 0),
            "address_prior_flag_count": float(flagged),
            "address_flag_rate": float(flagged / max(total, 1)),
        }
    except Exception as e:
        logger.warning(f"address_cluster_score failed: {e}")
        return neutral


def session_burst_features(
    device_id: Any, phone: Any = "", db_path: Any = None
) -> Dict[str, float]:
    neutral = {"orders_last_10min": 0.0, "is_burst_session": 0.0}
    key = resolve_device_key(device_id, phone)
    if not key:
        return neutral
    try:
        conn = get_connection(db_path)
        try:
            row = conn.execute(
                """SELECT COUNT(*) AS c FROM orders
                   WHERE device_id = ?
                     AND scored_at >= datetime('now', '-10 minutes')""",
                (key,),
            ).fetchone()
        finally:
            conn.close()
        burst = int((row["c"] if row else 0) or 0)
        return {
            "orders_last_10min": float(burst),
            "is_burst_session": float(1 if burst >= 2 else 0),
        }
    except Exception as e:
        logger.warning(f"session_burst_features failed: {e}")
        return neutral


def value_trajectory_features(
    device_id: Any, current_value: Any, phone: Any = "", db_path: Any = None
) -> Dict[str, float]:
    neutral = {"value_spike_vs_history": 0.0, "is_value_probe_exploit": 0.0}
    key = resolve_device_key(device_id, phone)
    if not key:
        return neutral
    try:
        current = float(current_value or 0.0)
    except Exception:
        return neutral
    try:
        conn = get_connection(db_path)
        try:
            rows = conn.execute(
                """SELECT order_value FROM orders
                   WHERE device_id = ?
                   ORDER BY scored_at DESC LIMIT 5""",
                (key,),
            ).fetchall()
        finally:
            conn.close()
        if not rows:
            return neutral
        vals = [float(r["order_value"] or 0.0) for r in rows]
        recent_avg = sum(vals) / max(len(vals), 1)
        spike_ratio = current / max(recent_avg, 1)
        return {
            "value_spike_vs_history": round(float(spike_ratio), 2),
            "is_value_probe_exploit": float(
                1 if (spike_ratio > 3.0 and recent_avg < 800) else 0
            ),
        }
    except Exception as e:
        logger.warning(f"value_trajectory_features failed: {e}")
        return neutral
