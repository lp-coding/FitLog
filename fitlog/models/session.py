from typing import Dict, Any, List, Optional
from ..db import get_db

def start_session(plan_id: int) -> int:
    """Startet eine neue Session für einen Plan und gibt die Session-ID zurück."""
    db = get_db()
    cur = db.execute("INSERT INTO sessions(plan_id) VALUES(?);", (plan_id,))
    db.commit()
    return cur.lastrowid

def add_log(session_id: int, exercise_id: int, weight: float, reps: int, note: str = "") -> int:
    """Speichert einen Trainingslog (Satz)."""
    db = get_db()
    cur = db.execute(
        "INSERT INTO logs(session_id, exercise_id, weight, reps, note) VALUES(?,?,?,?,?);",            (session_id, exercise_id, weight, reps, note),
    )
    db.commit()
    return cur.lastrowid

def get_latest_weights_by_plan(plan_id: int) -> List[Dict[str, Any]]:
    """Liefert pro Übung im Plan das zuletzt geloggte Gewicht (für Balkendiagramm)."""
    db = get_db()
    rows = db.execute(
        """SELECT e.name, COALESCE(
                (SELECT l.weight FROM logs l
                 JOIN sessions s ON s.id = l.session_id
                 WHERE l.exercise_id = e.id AND s.plan_id = pe.plan_id
                 ORDER BY l.created_at DESC LIMIT 1), pe.default_weight) AS weight
            FROM plan_exercises pe
            JOIN exercises e ON e.id = pe.exercise_id
            WHERE pe.plan_id=?
            ORDER BY e.name;""", (plan_id,)
    ).fetchall()
    return [dict(r) for r in rows]

def get_weight_progress(exercise_id: int) -> List[Dict[str, Any]]:
    """Gewichtsverlauf für eine Übung (zeitlich sortiert, für Liniendiagramm)."""
    db = get_db()
    rows = db.execute(
        """SELECT l.created_at as ts, l.weight
            FROM logs l
            WHERE l.exercise_id = ?
            ORDER BY l.created_at ASC;""", (exercise_id,)
    ).fetchall()
    return [dict(r) for r in rows]
