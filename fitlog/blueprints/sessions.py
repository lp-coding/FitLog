from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
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
    """Open a SQLite connection with row_factory=Row and FK enabled."""
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
# Schema-Helfer (robust bei optionalen Spalten)
# ------------------------------
def _table_has_column(db: sqlite3.Connection, table: str, column: str) -> bool:
    """True, falls Tabelle 'table' eine Spalte 'column' besitzt."""
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"].lower() == column.lower() for r in rows)


# ------------------------------
# Loader
# ------------------------------
def _load_session(db: sqlite3.Connection, session_id: int) -> sqlite3.Row:
    """Load session header + plan name (joins training_plans)."""
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
    Prefilled inputs for record form (eine Zeile je Übung):
      - Basis: alle Übungen aus dem Plan
      - Prefill-Priorität: session_entries > plan_exercises-Defaults
      - Notiz-Fallback: session_entries.note > plan_exercises.note > ''
      - Sätze: COALESCE(se.sets, pe.default_sets, 3)
        (Spalten 'sets' / 'default_sets' sind optional und werden nur gelesen, wenn vorhanden)
    """
    has_se_sets = _table_has_column(db, "session_entries", "sets")
    has_pe_sets = _table_has_column(db, "plan_exercises", "default_sets")

    se_sets_expr = "se.sets" if has_se_sets else "NULL"
    pe_sets_expr = "pe.default_sets" if has_pe_sets else "NULL"

    sql = f"""
        SELECT
            e.id   AS exercise_id,
            e.name AS name,

            /* Sätze mit robustem Fallback auf 3 */
            COALESCE({se_sets_expr}, {pe_sets_expr}, 3) AS sets,

            COALESCE(se.reps,      pe.default_reps,       10) AS reps,
            COALESCE(se.weight_kg, pe.default_weight_kg,   0) AS weight_kg,
            COALESCE(se.note,      pe.note,               '') AS note
        FROM sessions s
        JOIN plan_exercises pe ON pe.plan_id   = s.plan_id
        JOIN exercises      e  ON e.id         = pe.exercise_id
        LEFT JOIN session_entries se
               ON se.session_id  = s.id
              AND se.exercise_id = e.id
        WHERE s.id = ?
        ORDER BY COALESCE(pe.position, 999999), e.name COLLATE NOCASE
    """
    return db.execute(sql, (session_id,)).fetchall()


def _update_plan_defaults_from_session(
    db: sqlite3.Connection,
    plan_id: int,
    session_id: int,
) -> None:
    """Update per-plan default weights from the latest session.

    Für jede Übung, die in dieser Session mit einem positiven Gewicht
    geloggt wurde, wird das entsprechende `default_weight_kg` im
    `plan_exercises`-Eintrag des zugehörigen Plans aktualisiert.

    Effekt: Beim nächsten Training werden automatisch die zuletzt
    geschafften Gewichte als Standard vorgeschlagen.
    """
    rows = db.execute(
        """
        SELECT exercise_id, weight_kg
          FROM session_entries
         WHERE session_id = ?
           AND weight_kg IS NOT NULL
        """,
        (session_id,),
    ).fetchall()

    for row in rows:
        weight = row["weight_kg"]
        ex_id = row["exercise_id"]

        # Nur sinnvolle, positive Gewichte übernehmen
        try:
            w = float(weight)
        except (TypeError, ValueError):
            continue
        if w <= 0:
            continue

        db.execute(
            """
            UPDATE plan_exercises
               SET default_weight_kg = ?
             WHERE plan_id     = ?
               AND exercise_id = ?
            """,
            (w, plan_id, ex_id),
        )


def _upsert_entries(db: sqlite3.Connection, session_id: int, form: Dict[str, Any]) -> None:
    """
    Write one aggregate row per exercise into session_entries.
    Unterstützte Formnamen:
      A) ex[<id>][sets|reps|weight|note]
      B) flat: exercise_id + sets_<id>, reps_<id>, weight_<id>, note_<id>

    Besonderheiten:
      - Sätze 0..99 (0 = Übung ausgelassen -> kein Speichern)
      - Spalte 'sets' ist optional: wird nur beschrieben, wenn vorhanden
    """
    # Parser (falls vorhanden) darf liefern; ansonsten fallen wir auf eigenes Parsing zurück
    try:
        from fitlog.services.record_parser import parse_exercises_form
        parsed = parse_exercises_form(form)  # Dict[int, Dict[str, Any]]
    except Exception:
        parsed = {}

    has_se_sets = _table_has_column(db, "session_entries", "sets")

    # Alle exercise_ids aus dem Formular
    exercise_ids = request.form.getlist("exercise_id")
    # Fallback: falls Template keine hidden exercise_id setzt, versuche IDs aus Keys zu parsen
    if not exercise_ids:
        # Suche nach ex[<id>][...] oder <field>_<id>
        for key in form.keys():
            if key.startswith("ex["):
                try:
                    part = key.split("[", 1)[1]
                    ex_id = int(part.split("]")[0])
                    exercise_ids.append(str(ex_id))
                except Exception:
                    pass
            elif "_" in key:
                suffix = key.rsplit("_", 1)[-1]
                if suffix.isdigit():
                    exercise_ids.append(suffix)
        # deduplizieren
        exercise_ids = sorted(set(exercise_ids), key=lambda x: int(x) if x.isdigit() else 0)

    for raw_id in exercise_ids:
        try:
            ex_id = int(raw_id)
        except ValueError:
            continue

        # Keys der flachen Form
        sets_key   = f"sets_{ex_id}"
        reps_key   = f"reps_{ex_id}"
        weight_key = f"weight_{ex_id}"
        note_key   = f"note_{ex_id}"

        # Basiswerte
        sets_val: Optional[int] = None
        reps: Optional[int] = None
        weight: Optional[float] = None
        note: str = ""

        # 1. Versuch: geparstes Dict verwenden
        payload: Dict[str, Any] = parsed.get(ex_id, {})

        if "sets" in payload:
            try:
                sets_val = int(payload.get("sets"))
            except (TypeError, ValueError):
                sets_val = None
        elif sets_key in form:
            raw_sets = form.get(sets_key)
            if raw_sets:
                try:
                    sets_val = int(raw_sets)
                except ValueError:
                    sets_val = None

        if "reps" in payload:
            try:
                reps = int(payload.get("reps"))
            except (TypeError, ValueError):
                reps = None
        elif reps_key in form:
            raw_reps = form.get(reps_key)
            if raw_reps:
                try:
                    reps = int(raw_reps)
                except ValueError:
                    reps = None

        if "weight" in payload:
            try:
                weight = float(str(payload.get("weight")).replace(",", "."))
            except (TypeError, ValueError):
                weight = None
        elif weight_key in form:
            raw_weight = form.get(weight_key)
            if raw_weight:
                try:
                    weight = float(str(raw_weight).replace(",", "."))
                except ValueError:
                    weight = None

        if note_key in form:
            note = str(form.get(note_key) or "").strip()
        if "note" in payload:
            note = str(payload.get("note", note) or "").strip()

        # Wenn Sätze explizit 0 -> Übung ausgelassen -> keinen Datensatz speichern
        if sets_val is not None and sets_val == 0:
            # evtl. vorhandenen Eintrag löschen, damit „auslassen“ eindeutig ist
            db.execute(
                "DELETE FROM session_entries WHERE session_id = ? AND exercise_id = ?",
                (session_id, ex_id),
            )
            continue

        # Dynamisches INSERT/UPSERT (mit optionaler Spalte 'sets')
        values = [session_id, ex_id, weight, reps, note, _utcnow_iso()]
        if has_se_sets:
            # wir fügen 'sets' vor 'note' ein (Reihenfolge egal, aber semantisch schöner)
            insert_vals = [session_id, ex_id, weight, reps, (sets_val if sets_val is not None else 3), note, _utcnow_iso()]
            sql = """
                INSERT INTO session_entries (session_id, exercise_id, weight_kg, reps, sets, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, exercise_id) DO UPDATE SET
                  weight_kg = excluded.weight_kg,
                  reps      = excluded.reps,
                  sets      = excluded.sets,
                  note      = excluded.note,
                  created_at= excluded.created_at
            """
            db.execute(sql, insert_vals)
        else:
            # kein 'sets' in Tabelle -> altes, kompatibles Verhalten
            sql = """
                INSERT INTO session_entries (session_id, exercise_id, weight_kg, reps, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, exercise_id) DO UPDATE SET
                  weight_kg = excluded.weight_kg,
                  reps      = excluded.reps,
                  note      = excluded.note,
                  created_at= excluded.created_at
            """
            db.execute(sql, values)


# ------------------------------
# Routen
# ------------------------------
@bp.get("/new")
def new_session():
    """Neue Session für einen Plan anlegen und zur Erfassungsmaske springen."""
    db = get_db()

    # plan_id aus Query-Param (?plan_id=...)
    plan_id = request.args.get("plan_id", type=int)
    if plan_id is None:
        db.close()
        abort(400, description="plan_id is required")

    # prüfen, ob Plan existiert
    plan = db.execute(
        "SELECT id, name FROM training_plans WHERE id = ? AND deleted_at IS NULL",
        (plan_id,),
    ).fetchone()

    if not plan:
        db.close()
        abort(404)

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
    """Erfassungsmaske für eine laufende Session anzeigen."""
    db = get_db()
    sess = _load_session(db, session_id)
    items = _load_record_items(db, session_id)
    db.close()
    return render_template(
        "sessions/record.html",
        session=sess,  # optional alias, falls irgendwo 'session' verwendet wird
        sess=sess,     # wichtig: so heißt es im Template
        items=items,
    )



@bp.post("/<int:session_id>/record")
def record_session_post(session_id: int):
    """Zwischenspeichern der Eingaben, Session bleibt offen."""
    db = get_db()
    _ = _load_session(db, session_id)
    _upsert_entries(db, session_id, request.form)
    db.commit()
    db.close()
    flash("Zwischenspeicherung erfolgreich", "success")
    return redirect(url_for("sessions.record_session", session_id=session_id))


@bp.post("/<int:session_id>/finish")
def finish_session(session_id: int):
    """Training speichern & beenden."""
    db = get_db()
    sess = _load_session(db, session_id)
    _upsert_entries(db, session_id, request.form)

    # Optional: Dauer in Minuten
    raw_minutes = request.form.get("duration_minutes_override")
    if not raw_minutes:
        # Alias unterstützen (z. B. neues Template-Feld 'duration_minutes')
        raw_minutes = request.form.get("duration_minutes")

    if raw_minutes:
        try:
            mins = max(0.0, float(str(raw_minutes).replace(",", ".").strip()))
        except ValueError:
            mins = 0.0
    else:
        mins = 0.0

    if mins > 0.0:
        try:
            start_dt = datetime.fromisoformat(sess["started_at"])
        except Exception:
            start_dt = datetime.utcnow()
        ended_at_iso = (start_dt + timedelta(minutes=mins)).isoformat(timespec="seconds")
        db.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (ended_at_iso, session_id))
    else:
        # klassischer „Training beenden“-Klick -> Ende jetzt, falls nicht schon gesetzt
        db.execute(
            "UPDATE sessions SET ended_at = COALESCE(ended_at, ?) WHERE id = ?",
            (_utcnow_iso(), session_id),
        )

    # Nach Abschluss der Session: Standardgewichte im Plan aktualisieren
    _update_plan_defaults_from_session(db, sess["plan_id"], session_id)

    db.commit()
    db.close()
    flash("Training wurde gespeichert", "success")
    return redirect(url_for("index"))


@bp.post("/<int:session_id>/abort")
def abort_session(session_id: int):
    """Training abbrechen – löscht Session und Einträge."""
    db = get_db()
    _ = _load_session(db, session_id)
    db.execute("DELETE FROM session_entries WHERE session_id = ?", (session_id,))
    db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    db.commit()
    db.close()
    flash("Training abgebrochen.", "info")
    return redirect(url_for("index"))
