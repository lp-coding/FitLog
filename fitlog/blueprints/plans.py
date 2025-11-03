from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash
from ..db import get_db

bp = Blueprint("plans", __name__, url_prefix="/plans")

@bp.get("/")
def list_plans():
    """JSON: alle Trainingspläne."""
    db = get_db()
    rows = db.execute(
        "SELECT id, name FROM training_plans ORDER BY id DESC"
    ).fetchall()
    return jsonify([dict(r) for r in rows])

@bp.get("/page")
def list_plans_page():
    """HTML: Liste der Trainingspläne."""
    db = get_db()
    rows = db.execute("SELECT id, name FROM training_plans ORDER BY id DESC").fetchall()
    return render_template("plans/list.html", plans=rows)

@bp.post("/create")
def create_plan():
    """Legt einen neuen Plan an (aus HTML-Formular)."""
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Bitte einen Namen angeben.", "error")
        return redirect(url_for("plans.list_plans_page"))

    db = get_db()
    try:
        db.execute("INSERT INTO training_plans (name) VALUES (?)", (name,))
        db.commit()
        flash(f"Plan „{name}“ erstellt.", "success")
    except Exception:
        # häufigster Grund: UNIQUE-Constraint (Name schon vorhanden)
        flash("Konnte Plan nicht erstellen (Name evtl. bereits vorhanden).", "error")
    return redirect(url_for("plans.list_plans_page"))

# Detailseite eines Plans + Formular zum Hinzufügen einer Übung
@bp.get("/<int:plan_id>")
def plan_detail(plan_id: int):
    db = get_db()

    # Plan laden
    plan = db.execute(
        "SELECT id, name FROM training_plans WHERE id = ?",
        (plan_id,),
    ).fetchone()
    if not plan:
        return ("Plan nicht gefunden", 404)

    # Bereits verknüpfte Übungen (mit Reihenfolge)
    exercises_in_plan = db.execute(
        """
        SELECT e.id, e.name, e.muscle_group, pe.position
        FROM plan_exercises AS pe
        JOIN exercises AS e ON e.id = pe.exercise_id
        WHERE pe.plan_id = ?
        ORDER BY COALESCE(pe.position, 9999), e.name
        """,
        (plan_id,),
    ).fetchall()

    # Alle verfügbaren Übungen (für Dropdown); optional: exclude already added
    all_exercises = db.execute(
        """
        SELECT id, name FROM exercises
        ORDER BY name
        """
    ).fetchall()

    return render_template(
        "plans/detail.html",
        plan=plan,
        exercises_in_plan=exercises_in_plan,
        all_exercises=all_exercises,
    )

@bp.post("/<int:plan_id>/add-exercise")
def add_exercise(plan_id: int):
    db = get_db()
    exercise_id = request.form.get("exercise_id", type=int)
    position = request.form.get("position", type=int)

    if not exercise_id:
        flash("Bitte eine Übung auswählen.", "error")
        return redirect(url_for("plans.plan_detail", plan_id=plan_id))

    try:
        db.execute(
            "INSERT INTO plan_exercises (plan_id, exercise_id, position) VALUES (?, ?, ?)",
            (plan_id, exercise_id, position),
        )
        db.commit()
        flash("Übung zum Plan hinzugefügt.", "success")
    except Exception:
        # Häufigster Grund: UNIQUE-Constraint -> Übung bereits im Plan
        flash("Diese Übung ist in diesem Plan bereits enthalten.", "error")

    return redirect(url_for("plans.plan_detail", plan_id=plan_id))
