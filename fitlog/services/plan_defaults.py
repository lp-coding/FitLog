from datetime import datetime
from fitlog import db
from fitlog.models import PlanExercise

def maybe_update_plan_defaults(plan_id, exercise_id, sets, reps, weight, notes):
    """Aktualisiert Standardwerte des Plans (optional)."""
    pe = PlanExercise.query.filter_by(plan_id=plan_id, exercise_id=exercise_id).first()
    if not pe:
        return

    changed = False
    if sets and sets > 0 and pe.default_sets != sets:
        pe.default_sets = sets; changed = True
    if reps and pe.default_reps != reps:
        pe.default_reps = reps; changed = True
    if weight and pe.default_weight != weight:
        pe.default_weight = weight; changed = True
    if notes and notes.strip() and pe.default_notes != notes.strip():
        pe.default_notes = notes.strip(); changed = True

    if changed:
        pe.updated_at = datetime.utcnow()
        db.session.add(pe)
