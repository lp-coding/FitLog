import sqlite3
from pathlib import Path
from flask import current_app, g

def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = Path(current_app.instance_path) / "fitlog.db"
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")   # <- wichtig
    return g.db
