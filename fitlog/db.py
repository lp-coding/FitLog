# fitlog/db.py
from __future__ import annotations
import sqlite3
from pathlib import Path
from flask import current_app, g

def get_db() -> sqlite3.Connection:
    """
    Returns a cached SQLite connection bound to the current request context.
    Row factory = dict-ähnliche Zugriffe via Spaltennamen.
    """
    if "db" not in g:
        db_path = Path(current_app.instance_path) / "fitlog.db"
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(_: Exception | None = None) -> None:
    """Closes the connection at the end of the request (if present)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()
