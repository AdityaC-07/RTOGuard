"""Small persistence and retraining primitives for confirmed outcomes."""

import pickle
import os
import sqlite3
from pathlib import Path
from typing import Any

def should_retrain(db_path: str = "data/orders.db") -> bool:
    if not os.path.exists(db_path):
        return False
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM orders WHERE confirmed_rto IS NOT NULL"
        ).fetchone()
    count = int(row["c"] if row else 0)
    return count >= 500 and count % 200 == 0


def save_model(model: Any, path: str = "data/model.pkl") -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        pickle.dump(model, handle)
    return str(target)


def load_model(path: str = "data/model.pkl") -> Any:
    with Path(path).open("rb") as handle:
        return pickle.load(handle)


def confirmed_label_count(db_path: str = None) -> int:
    from app.db.connection import get_connection
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE confirmed_rto != 0").fetchone()
        return int(row["c"] if row else 0)
    finally:
        conn.close()