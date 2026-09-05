"""Best-effort IP intelligence with a neutral, offline-safe fallback."""

import ipaddress
from typing import Dict

import httpx

IP_FEATURE_NAMES = [
    "ip_is_private", "ip_is_loopback", "ip_order_count_24h",
    "ip_distinct_phones", "ip_is_vpn", "ip_country_mismatch",
    "ip_isp_is_datacenter",
]


def ip_features(ip_address: str, db_path: str = None) -> Dict[str, float]:
    value = str(ip_address or "").strip()
    result = {name: 0.0 for name in IP_FEATURE_NAMES}
    try:
        parsed = ipaddress.ip_address(value)
        result["ip_is_private"] = float(parsed.is_private)
        result["ip_is_loopback"] = float(parsed.is_loopback)
    except ValueError:
        return result
    if db_path:
        try:
            from app.db.connection import get_connection
            conn = get_connection(db_path)
            try:
                row = conn.execute(
                    """SELECT COUNT(*) AS orders, COUNT(DISTINCT phone) AS phones
                       FROM orders WHERE ip_address = ?
                       AND scored_at >= datetime('now', '-1 day')""",
                    (value,),
                ).fetchone()
                if row:
                    result["ip_order_count_24h"] = float(row["orders"] or 0)
                    result["ip_distinct_phones"] = float(row["phones"] or 0)
            finally:
                conn.close()
        except Exception:
            pass
    if result["ip_is_private"] or result["ip_is_loopback"]:
        return result
    try:
        response = httpx.get(
            f"http://ip-api.com/json/{value}?fields=status,country,proxy,hosting",
            timeout=0.2,
        )
        data = response.json()
        if data.get("status") == "success":
            result["ip_country_mismatch"] = float(data.get("country") != "India")
            result["ip_is_vpn"] = float(bool(data.get("proxy")))
            result["ip_isp_is_datacenter"] = float(bool(data.get("hosting")))
    except Exception:
        pass
    return result