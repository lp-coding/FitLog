from flask import Blueprint, render_template, request, redirect, url_for
from ..models import session as session_model, plan as plan_model

bp = Blueprint("training", __name__, url_prefix="/train")

@bp.route("/<int:plan_id>", methods=["GET", "POST"]) 
def start(plan_id: int):
    """Startet/bedient eine Trainingserfassung."""
    if request.method == "POST":
        session_id = int(request.form["session_id"])
        exercise_id = int(request.form["exercise_id"])
        weight = float(request.form.get("weight", 0) or 0)
        reps = int(request.form.get("reps", 0) or 0)
        note = request.form.get("note", "")
        session_model.add_log(session_id, exercise_id, weight, reps, note)
        return redirect(url_for("training.start", plan_id=plan_id))

    # GET: Session erzeugen, Plan-Daten laden
    data = plan_model.get_plan(plan_id)
    if not data:
        return redirect(url_for("plans.list_view"))
    session_id = session_model.start_session(plan_id)
    return render_template("training.html", plan=data, session_id=session_id)
