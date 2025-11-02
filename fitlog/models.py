import sqlite3
from flask import g
from .db import get_db


def create_training_plan(name: str) -> int:
    """Erstellt einen neuen Trainingsplan und gibt die ID zurück."""
    db = get_db()
    cur = db.execute("INSERT INTO training_plans (name) VALUES (?)", (name,))
    db.commit()
    return cur.lastrowid


def get_all_plans() -> list[sqlite3.Row]:
    """Liefert alle Trainingspläne (z. B. für Übersicht)."""
    db = get_db()
    return db.execute("SELECT id, name FROM training_plans ORDER BY id DESC").fetchall()


def add_exercise_to_plan(plan_id: int, exercise_id: int) -> None:
    """Verknüpft eine Übung mit einem Plan."""
    db = get_db()
    db.execute(
        "INSERT INTO plan_exercises (plan_id, exercise_id) VALUES (?, ?)",
        (plan_id, exercise_id),
    )
    db.commit()
