import sqlite3
from flask import current_app, g
from pathlib import Path
from typing import Optional

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    met REAL DEFAULT 6.0
);

CREATE TABLE IF NOT EXISTS plan_exercises (
    plan_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    default_weight REAL DEFAULT 0,
    PRIMARY KEY (plan_id, exercise_id),
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    weight REAL NOT NULL,
    reps INTEGER NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
);
"""

def get_db() -> sqlite3.Connection:
    """Stellt eine Verbindung zur SQLite-DB her und cached sie im Flask-Kontext."""
    if "db" not in g:
        db_path = Path(current_app.instance_path) / current_app.config["DATABASE"]
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e: Optional[BaseException] = None) -> None:
    """Schließt die DB-Verbindung am Ende der Anfrage."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db(app) -> None:
    """Registriert Teardown-Handler und legt Schema an (falls noch nicht vorhanden)."""
    app.teardown_appcontext(close_db)
    # Schema anlegen
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA_SQL)
        db.commit()
        # Seed: ein paar Standard-Übungen (nur beim ersten Mal wirksam durch UNIQUE)
        seed = [
            ("Bench Press", 6.0),
            ("Lat Pulldown", 6.0),
            ("Seated Row", 6.0),
            ("Shoulder Press", 6.0),
            ("Biceps Curl", 3.5),
            ("Squat", 7.0),
        ]
        db.executemany("INSERT OR IGNORE INTO exercises(name, met) VALUES(?, ?);", seed)
        db.commit()
