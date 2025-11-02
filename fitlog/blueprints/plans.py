# fitlog/blueprints/plans.py
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
