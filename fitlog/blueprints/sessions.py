# fitlog/blueprints/sessions.py
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from ..db import get_db

bp = Blueprint("sessions", __name__, url_prefix="/sessions")


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


@bp.get("/new")
def new_session():
    """Plan wählen und Session starten."""
    db = get_db()
    plans = db.execute(
        "SELECT id, name FROM training_plans WHERE deleted_at IS NULL ORDER BY name"
    ).fetchall()
    return render_template("sessions/new.html", plans=plans)


@bp.post("/create")
def create_session():
    """Neue Session anlegen und zur Erfassung springen."""
    plan_id = request.form.get("plan_id", type=int)
    if not plan_id:
        flash("Bitte einen Trainingsplan auswählen.", "error")
        return redirect(url_for("sessions.new_session"))

    db = get_db()
    plan = db.execute(
        "SELECT id FROM training_plans WHERE id = ? AND deleted_at IS NULL",
        (plan_id,),
    ).fetchone()
    if not plan:
        flash("Plan nicht gefunden oder archiviert.", "error")
        return redirect(url_for("sessions.new_session"))

    cur = db.execute(
        "INSERT INTO sessions (plan_id, started_at) VALUES (?, ?)",
        (plan_id, _utcnow_iso()),
    )
    db.commit()
    session_id = cur.lastrowid
    return redirect(url_for("sessions.record_session", session_id=session_id))


@bp.get("/<int:session_id>/record")
def record_session(session_id: int):
    """Erfassungsseite für eine laufende Session."""
    db = get_db()
    sess = db.execute(
        """
        SELECT s.id, s.plan_id, s.started_at, s.ended_at,
               p.name AS plan_name
        FROM sessions s
        JOIN training_plans p ON p.id = s.plan_id
        WHERE s.id = ?
        """,
        (session_id,),
    ).fetchone()
    if not sess:
        abort(404, "Session nicht gefunden.")

    # Plan-Übungen + Defaults aus plan_exercises laden
    items = db.execute(
        """
        SELECT e.id AS exercise_id,
               e.name,
               COALESCE(pe.default_weight_kg, 0) AS default_weight_kg,
               COALESCE(pe.default_reps, 10)      AS default_reps
        FROM plan_exercises pe
        JOIN exercises e ON e.id = pe.exercise_id
        WHERE pe.plan_id = ?
        ORDER BY COALESCE(pe.position, 9999), e.name
        """,
        (sess["plan_id"],),
    ).fetchall()

    # Bereits erfasste Werte für diese Session
    existing = db.execute(
        "SELECT exercise_id, weight_kg, reps, note FROM session_entries WHERE session_id = ?",
        (session_id,),
    ).fetchall()
    existing_map = {r["exercise_id"]: dict(r) for r in existing}

    # Prefill
    enriched = []
    for it in items:
        ex_id = it["exercise_id"]
        row = existing_map.get(ex_id)
        enriched.append(
            {
                "exercise_id": ex_id,
                "name": it["name"],
                "weight_kg": (row["weight_kg"] if row else it["default_weight_kg"]),
                "reps": (row["reps"] if row else it["default_reps"]),
                "note": (row["note"] if row else ""),
            }
        )

    return render_template("sessions/record.html", sess=sess, items=enriched)


def _upsert_entries(db, session_id: int, form) -> None:
    """Update falls vorhanden, sonst Insert – passend zu session_entries (PK=id)."""
    ex_ids = form.getlist("exercise_id", type=int)
    for ex_id in ex_ids:
        weight = form.get(f"weight_{ex_id}", type=float) or 0.0
        reps = form.get(f"reps_{ex_id}", type=int) or 0
        note = form.get(f"note_{ex_id}", "") or ""

        # erst Update versuchen …
        cur = db.execute(
            """
            UPDATE session_entries
               SET weight_kg = ?, reps = ?, note = ?
             WHERE session_id = ? AND exercise_id = ?
            """,
            (weight, reps, note, session_id, ex_id),
        )
        if cur.rowcount == 0:
            # … sonst Insert
            db.execute(
                """
                INSERT INTO session_entries (session_id, exercise_id, weight_kg, reps, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, ex_id, weight, reps, note),
            )


@bp.post("/<int:session_id>/save")
def save_session(session_id: int):
    """Zwischenspeichern und auf der Seite bleiben."""
    db = get_db()
    _upsert_entries(db, session_id, request.form)
    db.commit()
    flash("Zwischengespeichert.", "success")
    return redirect(url_for("sessions.record_session", session_id=session_id))


@bp.post("/<int:session_id>/finish")
def finish_session(session_id: int):
    """Training beenden: Werte sichern, Endzeit setzen, Defaults im Plan ggf. anpassen, zurück zur Startseite."""
    db = get_db()
    _upsert_entries(db, session_id, request.form)

    # Endzeit setzen
    db.execute(
        "UPDATE sessions SET ended_at = ? WHERE id = ? AND ended_at IS NULL",
        (_utcnow_iso(), session_id),
    )

    # Defaults der Plan-Übungen ggf. auf das zuletzt verwendete Gewicht setzen
    rows = db.execute(
        """
        SELECT s.plan_id, se.exercise_id, se.weight_kg,
               COALESCE(pe.default_weight_kg, 0) AS old_default
        FROM session_entries se
        JOIN sessions s ON s.id = se.session_id
        JOIN plan_exercises pe ON pe.plan_id = s.plan_id AND pe.exercise_id = se.exercise_id
        WHERE se.session_id = ?
        """,
        (session_id,),
    ).fetchall()

    for r in rows:
        new_w = float(r["weight_kg"] or 0)
        if new_w > 0 and new_w != float(r["old_default"]):
            db.execute(
                "UPDATE plan_exercises SET default_weight_kg = ? WHERE plan_id = ? AND exercise_id = ?",
                (new_w, r["plan_id"], r["exercise_id"]),
            )

    db.commit()
    flash("Training beendet. Daten gespeichert.", "success")
    return redirect(url_for("index"))
