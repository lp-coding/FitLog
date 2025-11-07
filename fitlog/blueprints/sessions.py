from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import sqlite3
from flask import Blueprint, current_app, render_template, request, redirect, url_for, abort, flash

# Blueprint
bp = Blueprint("sessions", __name__, url_prefix="/sessions")


# ------------------------------
# Infrastruktur / Utilities
# ------------------------------
def get_db() -> sqlite3.Connection:
    """
    Returns a sqlite3 connection using the configured DATABASE path.
    Expects row_factory=sqlite3.Row.
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
    """UTC Zeit in ISO (sekundengenau), ohne Z, kompatibel mit fromisoformat()."""
    return datetime.now(timezone.utc).astimezone(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


# ------------------------------
# Loader
# ------------------------------
def _load_session(db: sqlite3.Connection, session_id: int) -> sqlite3.Row:
    """
    Lädt eine Session inkl. Planname (aus training_plans).
    sessions: id, plan_id, started_at, ended_at, notes
    training_plans: id, name
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
    Liefert die Zeilen für die Record-Tabelle:
    - Alle Übungen des Plans (plan_exercises + exercises)
    - Linke Join auf bereits vorhandene Session-Einträge (session_entries)
    Prefill-Prio: vorhandene session_entries > plan_defaults
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
        ORDER BY pe.position NULLS LAST, e.name COLLATE NOCASE
        """,
        (session_id,),
    ).fetchall()


def _upsert_entries(db: sqlite3.Connection, session_id: int, form: Dict[str, Any]) -> None:
    """
    Schreibt/aktualisiert pro Übung genau EINE Zeile in session_entries (Aggregat: reps, weight, note).
    Erwartet Feldschema aus record.html:
      - mehrfach: exercise_id
      - weight_<id>, reps_<id>, note_<id>
    Zusätzlich unterstützt: das strukturierte Schema aus record_parser.parse_exercises_form()
    """
    # 1) bevorzugt das strukturierte Schema ex[<id>][reps|weight|note]
    try:
        from fitlog.services.record_parser import parse_exercises_form
        parsed = parse_exercises_form(form)  # Dict[int, Dict[str, Any]]
    except Exception:
        parsed = {}

    # 2) wenn parsed leer ist, auf flache Felder zurückgreifen
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

        # Falls gleichzeitig strukturierte Daten existieren, überschreiben diese (höhere Prio)
        payload = parsed.get(ex_id, {})
        reps = int(payload.get("reps", reps))
        weight = float(payload.get("weight", weight))
        note = str(payload.get("note", note))

        db.execute(
            """
            INSERT INTO session_entries (session_id, exercise_id, weight_kg, reps, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(session_id, exercise_id) DO
            UPDATE SET
                weight_kg = excluded.weight_kg,
                reps = excluded.reps,
                note = excluded.note,
                created_at= excluded.created_at
            """,
            (session_id, ex_id, weight, reps, note, _utcnow_iso()),
        )


# ------------------------------
# Routes
# ------------------------------
@bp.get("/<int:session_id>/record")
def record_session(session_id: int):
    """
    Zeigt die Erfassungsseite:
      - Session (sess)
      - Items (exercises mit Prefill)
    Hinweis: started_at wurde laut Vorgabe bereits beim Start (Homepage-Button) gesetzt.
    """
    db = get_db()
    sess = _load_session(db, session_id)
    items = _load_record_items(db, session_id)
    db.close()
    return render_template("sessions/record.html", sess=sess, items=items)


@bp.post("/<int:session_id>/save")
def save_session(session_id: int):
    """
    Optionales Zwischenspeichern:
    - übernimmt aktuelle Eingaben (reps/weight/note) in session_entries
    - verändert ended_at/status nicht
    """
    db = get_db()
    # validiert Session
    _ = _load_session(db, session_id)
    _upsert_entries(db, session_id, request.form)
    db.commit()
    db.close()
    # Zurück zur Record-Seite
    return redirect(url_for("sessions.record_session", session_id=session_id))


@bp.post("/<int:session_id>/finish")
def finish_session(session_id: int):
    """
    Training beenden:
     - speichert aktuelle Eingaben (wie save)
     - setzt ended_at
       * wenn 'duration_minutes_override' gesetzt: ended_at = started_at + Dauer
       * sonst: ended_at = jetzt (falls noch NULL)
     - setzt status='completed' (nur wenn noch nicht completed)
     - Redirect zur Plan-Detailseite
    """
    db = get_db()
    sess = _load_session(db, session_id)

    # Einträge übernehmen
    _upsert_entries(db, session_id, request.form)

    # Dauer-Override (Minuten) optional verarbeiten
    raw_minutes = request.form.get("duration_minutes_override")
    if raw_minutes:
        try:
            mins = max(0.0, float(str(raw_minutes).replace(",", ".").strip()))
        except ValueError:
            mins = 0.0
    else:
        mins = 0.0

    if mins > 0.0:
        # ended_at = started_at + mins
        if sess["started_at"]:
            try:
                start_dt = datetime.fromisoformat(sess["started_at"])
            except Exception:
                start_dt = datetime.utcnow()
        else:
            start_dt = datetime.utcnow()
        ended_at_iso = (start_dt + timedelta(minutes=mins)).isoformat(timespec="seconds")
        db.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (ended_at_iso, session_id),
        )
    else:
        # Standard: jetzt, aber nur setzen, wenn noch nicht gesetzt
        db.execute(
            "UPDATE sessions SET ended_at = COALESCE(ended_at, ?) WHERE id = ?",
            (_utcnow_iso(), session_id),
        )

    db.commit()
    db.close()

    # Erfolgshinweis und Redirect zur Startseite
    flash("Training wurde gespeichert", "success")
    return redirect(url_for("index"))


@bp.post("/<int:session_id>/abort")
def abort_session(session_id: int):
    """
    Hard-Abort (MVP): löscht Session und zugehörige Einträge.
    Achtung: Historie geht verloren – für Soft-Delete später anpassen.
    """
    db = get_db()
    # sicherstellen, dass Session existiert
    _ = _load_session(db, session_id)
    db.execute("DELETE FROM session_entries WHERE session_id = ?", (session_id,))
    db.execute("DELETE FROM sessions        WHERE id = ?", (session_id,))
    db.commit()
    db.close()
    # Zurück zur Planliste (oder Startseite)
    return redirect(url_for("index"))  # falls du 'plans.page' nutzt; ggf. zu 'plans.list_plans' anpassen

@bp.get("/new", endpoint="new_session")
def new_session():
    """
    Neue Session anlegen und direkt zur Erfassung leiten.
    - Wenn ?plan_id fehlt: nimm ersten aktiven Plan.
    - started_at wird jetzt explizit gesetzt (alternativ tut das deine DB per DEFAULT).
    """
    db = get_db()
    plan_id = request.args.get("plan_id", type=int)

    if not plan_id:
        row = db.execute(
            "SELECT id FROM training_plans WHERE deleted_at IS NULL ORDER BY name LIMIT 1"
        ).fetchone()
        if not row:
            db.close()
            return redirect(url_for("plans.page"))  # ggf. an deine Startseite anpassen
        plan_id = row["id"]

    started_at = _utcnow_iso()
    cur = db.execute(
        "INSERT INTO sessions (plan_id, started_at) VALUES (?, ?)",
        (plan_id, started_at),
    )
    session_id = cur.lastrowid
    db.commit()
    db.close()
    return redirect(url_for("sessions.record_session", session_id=session_id))

