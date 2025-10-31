from typing import List, Optional, Tuple, Dict, Any
from ..db import get_db

def list_plans() -> List[Dict[str, Any]]:
    """Liest alle Trainingspläne aus."""
    db = get_db()
    rows = db.execute("SELECT id, name FROM plans ORDER BY name;").fetchall()
    return [dict(r) for r in rows]

def create_plan(name: str) -> int:
    """Erstellt einen neuen Plan und gibt die ID zurück."""
    db = get_db()
    cur = db.execute("INSERT INTO plans(name) VALUES(?);", (name,))
    db.commit()
    return cur.lastrowid

def delete_plan(plan_id: int) -> None:
    """Löscht einen Plan (CASCADE löscht Zuordnungen und Sessions)."""
    db = get_db()
    db.execute("DELETE FROM plans WHERE id=?;", (plan_id,))
    db.commit()

def get_plan(plan_id: int) -> Optional[Dict[str, Any]]:
    """Liest einen Plan mit seinen Übungen."""
    db = get_db()
    plan = db.execute("SELECT id, name FROM plans WHERE id=?;", (plan_id,)).fetchone()
    if not plan:
        return None
    exercises = db.execute(
        """SELECT e.id, e.name, pe.default_weight
            FROM plan_exercises pe
            JOIN exercises e ON e.id = pe.exercise_id
            WHERE pe.plan_id=?
            ORDER BY e.name;""", (plan_id,)
    ).fetchall()
    data = dict(plan)
    data["exercises"] = [dict(r) for r in exercises]
    return data

def add_exercise_to_plan(plan_id: int, exercise_id: int, default_weight: float = 0.0) -> None:
    """Fügt eine Übung mit Standardgewicht zu einem Plan hinzu."""
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO plan_exercises(plan_id, exercise_id, default_weight) VALUES(?,?,?);",            (plan_id, exercise_id, default_weight),
    )
    db.commit()

def remove_exercise_from_plan(plan_id: int, exercise_id: int) -> None:
    """Entfernt eine Übung aus einem Plan."""
    db = get_db()
    db.execute("DELETE FROM plan_exercises WHERE plan_id=? AND exercise_id=?;", (plan_id, exercise_id))
    db.commit()

def list_exercises() -> List[Dict[str, Any]]:
    """Gibt alle verfügbaren Übungen zurück."""
    db = get_db()
    rows = db.execute("SELECT id, name, met FROM exercises ORDER BY name;").fetchall()
    return [dict(r) for r in rows]
