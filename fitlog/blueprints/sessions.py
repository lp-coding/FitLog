from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
import sqlite3

from flask import (
    Blueprint, current_app, render_template, request,
    redirect, url_for, abort, flash
)

bp = Blueprint("sessions", __name__, url_prefix="/sessions")


# ------------------------------
# DB Infrastruktur
# ------------------------------
def get_db() -> sqlite3.Connection:
    """
    Open a SQLite connection with row_factory=Row and FK enabled.
    """
    db_path = current_app.config.get("DATABASE")
    if not db_path:
        from pathlib import Path
        db_path = str(Path(current_app.instance_path) / "fitlog.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _utcnow_iso() -> str:
    """UTC timestamp ISO (seconds)."""
    return (
        datetime.now(timezone.utc)
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
        .isoformat(timespec="seconds")
    )


# ------------------------------
# Loader
# ------------------------------
def _load_session(db: sqlite3.Connection, session_id: int) -> sqlite3.Row:
    """
    Load session header + plan name (joins training_plans).
    """
    row = db.execute(
        """
        SELECT
            s.id,
            s.plan_id,
            s.started_at,
            s.ended_at,
            tp.name AS plan_name
        FROM sessions s
        JOIN training_plans tp ON tp.id = s.plan_id
        WHERE s.id = ?
        """,
        (session_id,),
    ).fetchone()
    if not row:
        abort(404)
    return row


def _load_record_items(db: sqlite3.Connection, session_id: int) -> List[sqlite3.Row]:
    """
    Prefilled inputs for record form:
    - base: all exercises of the plan
    - prefill priority: session_entries > plan_exercises defaults
    - note fallback: session_entries.note > plan_exercises.note > ''
    """
    return db.execute(
        """
        SELECT
            e.id   AS exercise_id,
            e.name AS name,
            COALESCE(se.reps,      pe.default_reps,       10) AS reps,
            COALESCE(se.weight_kg, pe.default_weight_kg,   0) AS weight_kg,
            COALESCE(se.note, pe.note, '')                   AS note
        FROM sessions s
        JOIN plan_exercises pe ON pe.plan_id   = s.plan_id
        JOIN exercises      e  ON e.id         = pe.exercise_id
        LEFT JOIN session_entries se
               ON se.session_id  = s.id
              AND se.exercise_id = e.id
        WHERE s.id = ?
        ORDER BY COALESCE(pe.position, 999999), e.name COLLATE NOCASE
        """,
        (session_id,),
    ).fetchall()


def _upsert_entries(db: sqlite3.Connection, session_id: int, form: Dict[str, Any]) -> None:
    """
    Write one aggregate row per exercise into session_entries.
    Supports two shapes:
      A) ex[<id>][reps|weight|note] from record_parser
      B) flat: exercise_id + reps_<id>, weight_<id>, note_<id>
    """
    # Try structured payload
    try:
        from fitlog.services.record_parser import parse_exercises_form
        parsed = parse_exercises_form(form)  # Dict[int, Dict[str, Any]]
    except Exception:
        parsed = {}

    # Fallback to flat fields
    exercise_ids = request.form.getlist("exercise_id")
    for raw_id in exercise_ids:
        try:
            ex_id = int(raw_id)
        except ValueError:
            continue

        reps_key = f"reps_{ex_id}"
        weight_key = f"weight_{ex_id}"
        note_key = f"note_{ex_id}"

        reps = 0
        weight = 0.0
        note = ""

        if reps_key in form:
            try:
                reps = max(0, int(str(form[reps_key]).strip()))
            except ValueError:
                reps = 0

        if weight_key in form:
            try:
                weight = max(0.0, float(str(form[weight_key]).replace(",", ".").strip()))
            except ValueError:
                weight = 0.0

        if note_key in form:
            note = (form[note_key] or "").strip()

        # structured has priority
        payload = parsed.get(ex_id, {})
        reps = int(payload.get("reps", reps))
        weight = float(payload.get("weight", weight))
        note = str(payload.get("note", note))

        db.execute(
            """
            INSERT INTO session_entries (session_id, exercise_id, weight_kg, reps, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, exercise_id) DO UPDATE SET
              weight_kg = excluded.weight_kg,
              reps      = excluded.reps,
              note      = excluded.note,
              created_at= excluded.created_at
            """,
            (session_id, ex_id, weight, reps, note, _utcnow_iso()),
        )


# ------------------------------
# Routes
# ------------------------------
@bp.get("/new", endpoint="new_session")
@bp.get("/new", endpoint="new_session")
def new_session():
    """
    Neue Session starten – NUR mit plan_id.
    Wenn keine plan_id übergeben wurde, zurück zur Startseite mit Hinweis.
    """
    plan_id = request.args.get("plan_id", type=int)
    if not plan_id:
        flash("Bitte zuerst einen Trainingsplan auswählen.", "info")
        return redirect(url_for("index"))

    db = get_db()
    started_at = _utcnow_iso()
    cur = db.execute(
        "INSERT INTO sessions (plan_id, started_at) VALUES (?, ?)",
        (plan_id, started_at),
    )
    session_id = cur.lastrowid
    db.commit()
    db.close()

    return redirect(url_for("sessions.record_session", session_id=session_id))



@bp.get("/<int:session_id>/record")
def record_session(session_id: int):
    db = get_db()
    sess = _load_session(db, session_id)
    items = _load_record_items(db, session_id)
    db.close()
    return render_template("sessions/record.html", sess=sess, items=items)


@bp.post("/<int:session_id>/finish")
def finish_session(session_id: int):
    """
    Save inputs, set ended_at.
    If duration_minutes_override provided: ended = started + minutes,
    else ended = now (if not yet set).
    Redirect to homepage with success flash.
    """
    db = get_db()
    sess = _load_session(db, session_id)

    _upsert_entries(db, session_id, request.form)

    raw_minutes = request.form.get("duration_minutes_override")
    if raw_minutes:
        try:
            mins = max(0.0, float(str(raw_minutes).replace(",", ".").strip()))
        except ValueError:
            mins = 0.0
    else:
        mins = 0.0

    if mins > 0.0:
        if sess["started_at"]:
            try:
                start_dt = datetime.fromisoformat(sess["started_at"])
            except Exception:
                start_dt = datetime.utcnow()
        else:
            start_dt = datetime.utcnow()
        ended_at_iso = (start_dt + timedelta(minutes=mins)).isoformat(timespec="seconds")
        db.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (ended_at_iso, session_id))
    else:
        db.execute(
            "UPDATE sessions SET ended_at = COALESCE(ended_at, ?) WHERE id = ?",
            (_utcnow_iso(), session_id),
        )

    db.commit()
    db.close()
    flash("Training wurde gespeichert ✅", "success")
    return redirect(url_for("index"))


@bp.post("/<int:session_id>/abort")
def abort_session(session_id: int):
    """
    Cancel session (MVP): delete header and entries, then go home.
    """
    db = get_db()
    _ = _load_session(db, session_id)  # 404 if not exists
    db.execute("DELETE FROM session_entries WHERE session_id = ?", (session_id,))
    db.execute("DELETE FROM sessions        WHERE id = ?", (session_id,))
    db.commit()
    db.close()
    flash("Training abgebrochen.", "info")
    return redirect(url_for("index"))
