"""SQLite order-history store for Phase 2 behavioural signals.

Every scored order is persisted here so future scores can see cross-order
patterns (device rotation, address clusters, session bursts, value
trajectories). SQLite is stdlib — no new dependencies.

Day-1 safety: an empty or missing DB yields neutral defaults everywhere;
callers must never raise because of storage.
"""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("rtoguard.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id TEXT,
  device_id TEXT,
  phone TEXT,
  pincode TEXT,
  address_token TEXT,
  order_value REAL,
  risk_score INTEGER,
  decision TEXT,
  behavior_json TEXT,
  confirmed_rto INTEGER DEFAULT 0,
  scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_orders_device ON orders(device_id, scored_at);
CREATE INDEX IF NOT EXISTS idx_orders_addr ON orders(address_token, scored_at);
CREATE INDEX IF NOT EXISTS idx_orders_order ON orders(order_id);
"""


def _default_path() -> str:
    root = Path(__file__).resolve().parents[2]
    return str(root / "data" / "orders.db")


def resolve_db_path(explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit
    return os.environ.get("RTOGUARD_DB_PATH", _default_path())


def init_db(db_path: Optional[str] = None) -> str:
    path = resolve_db_path(db_path)
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"init_db failed for {path}: {e}")
    return path


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = init_db(db_path)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def insert_order(record: Dict[str, Any], db_path: Optional[str] = None) -> int:
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """INSERT INTO orders
               (order_id, device_id, phone, pincode, address_token,
                order_value, risk_score, decision, behavior_json, confirmed_rto)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(record.get("order_id", "")),
                str(record.get("device_id", "UNKNOWN")),
                str(record.get("phone", "")),
                str(record.get("pincode", "")),
                str(record.get("address_token", "")),
                float(record.get("order_value", 0.0) or 0.0),
                int(record.get("risk_score", 0) or 0),
                str(record.get("decision", "APPROVE")),
                record.get("behavior_json"),
                int(record.get("confirmed_rto", 0) or 0),
            ),
        )
        conn.commit()
        return int(cur.lastrowid or 0)
    finally:
        conn.close()


def update_confirmation(
    order_id: str, confirmed: bool = True, db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Mark an order confirmed-RTO. Confirmed rows also flip to
    FLAG_FOR_REVIEW so device flag-rate queries pick them up."""
    conn = get_connection(db_path)
    try:
        if confirmed:
            conn.execute(
                """UPDATE orders SET confirmed_rto = 1, decision = 'FLAG_FOR_REVIEW'
                   WHERE order_id = ?""",
                (str(order_id),),
            )
        else:
            conn.execute(
                "UPDATE orders SET confirmed_rto = 0 WHERE order_id = ?",
                (str(order_id),),
            )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM orders WHERE order_id = ? ORDER BY id DESC LIMIT 1",
            (str(order_id),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
