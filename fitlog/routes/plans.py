from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..models import plan as plan_model

bp = Blueprint("plans", __name__, url_prefix="/plans")

@bp.route("/")
def list_view():
    """Zeigt alle Trainingspläne und ermöglicht schnelles Anlegen/Löschen."""
    plans = plan_model.list_plans()
    exercises = plan_model.list_exercises()
    return render_template("plans.html", plans=plans, exercises=exercises)

@bp.route("/new", methods=["POST"])  # simple POST aus dem Formular
def create():
    """Erzeugt einen neuen Trainingsplan."""
    name = request.form.get("name", "").strip()
    if not name:
        flash("Bitte einen Namen angeben.", "error")
        return redirect(url_for("plans.list_view"))
    plan_model.create_plan(name)
    flash("Plan angelegt.", "success")
    return redirect(url_for("plans.list_view"))

@bp.route("/<int:plan_id>")
def detail(plan_id: int):
    """Detailansicht eines Plans inkl. Übungen."""
    data = plan_model.get_plan(plan_id)
    if not data:
        flash("Plan nicht gefunden.", "error")
        return redirect(url_for("plans.list_view"))
    all_ex = plan_model.list_exercises()
    return render_template("plan_detail.html", plan=data, all_exercises=all_ex)

@bp.route("/<int:plan_id>/delete", methods=["POST"]) 
def delete(plan_id: int):
    """Löscht einen Plan."""
    plan_model.delete_plan(plan_id)
    flash("Plan gelöscht.", "success")
    return redirect(url_for("plans.list_view"))

@bp.route("/<int:plan_id>/add", methods=["POST"]) 
def add_exercise(plan_id: int):
    """Fügt eine Übung zum Plan hinzu."""
    ex_id = int(request.form.get("exercise_id"))
    default_weight = float(request.form.get("default_weight", 0) or 0)
    plan_model.add_exercise_to_plan(plan_id, ex_id, default_weight)
    return redirect(url_for("plans.detail", plan_id=plan_id))

@bp.route("/<int:plan_id>/remove", methods=["POST"]) 
def remove_exercise(plan_id: int):
    """Entfernt eine Übung aus dem Plan."""
    ex_id = int(request.form.get("exercise_id"))
    plan_model.remove_exercise_from_plan(plan_id, ex_id)
    return redirect(url_for("plans.detail", plan_id=plan_id))
