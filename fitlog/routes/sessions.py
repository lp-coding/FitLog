from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime
from fitlog import db
from fitlog.models import SessionEntry, TrainingSession
from fitlog.services.plan_defaults import maybe_update_plan_defaults

bp = Blueprint("sessions", __name__)

@bp.route("/sessions/<int:session_id>/record", methods=["GET", "POST"])
def record(session_id):
    session_obj = TrainingSession.query.get_or_404(session_id)

    if request.method == "GET":
        # Beispiel: Übungen & Defaults holen (hier Dummy)
        exercises = session_obj.plan.exercises
        selected_exercise_id = exercises[0].id if exercises else None
        defaults = exercises[0] if exercises else {}
        return render_template(
            "sessions/record.html",
            session=session_obj,
            exercises=exercises,
            selected_exercise_id=selected_exercise_id,
            defaults=defaults,
        )

    # POST
    form = request.form
    if form.get("action") == "cancel":
        flash("Eingabe verworfen.", "info")
        return redirect(url_for("sessions.view", session_id=session_id))

    sets   = _to_int(form.get("sets"))
    reps   = _to_int(form.get("reps"))
    weight = _to_float(form.get("weight"))
    notes  = (form.get("notes") or "").strip()
    exercise_id = int(form.get("exercise_id"))
    skipped = (sets == 0)

    entry = SessionEntry(
        session_id=session_id,
        exercise_id=exercise_id,
        sets=sets,
        reps=reps,
        weight=weight,
        notes=notes,
        skipped=skipped,
        created_at=datetime.utcnow(),
    )
    db.session.add(entry)

    if form.get("update_plan_defaults") == "1":
        maybe_update_plan_defaults(session_id, exercise_id, sets, reps, weight, notes)

    db.session.commit()
    flash("Training gespeichert.", "success")
    return redirect(url_for("sessions.view", session_id=session_id))


def _to_int(v):
    try:
        return int(v) if v not in (None, "",) else 0
    except ValueError:
        return 0


def _to_float(v):
    try:
        return float(v) if v not in (None, "",) else 0.0
    except ValueError:
        return 0.0
