from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import sqlite3

from flask import (
    Blueprint, current_app, render_template, request,
    redirect, url_for, abort, flash
)

# WICHTIG: Einheitlich dieselbe DB-Funktion wie der Rest der App nutzen
from fitlog.db import get_db

bp = Blueprint("sessions", __name__, url_prefix="/sessions")


# ------------------------------
# Zeit-Helper
# ------------------------------
def _utcnow_sqlite() -> str:
    """
    UTC Timestamp im SQLite-kompatiblen Format 'YYYY-MM-DD HH:MM:SS'.
    (Kein 'T' → dadurch ist datetime(...) in SQL robust.)
    """
    return (
        datetime.now(timezone.utc)
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
        .strftime("%Y-%m-%d %H:%M:%S")
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
    Prefilled inputs für das Erfassungsformular (eine Zeile je Übung):
      - Basis: alle Übungen aus dem Plan
      - Prefill-Priorität: session_entries > plan_exercises-Defaults
      - Notiz-Fallback: session_entries.note > plan_exercises.note > ''
      - Sätze: COALESCE(se.sets, pe.default_sets, 3)
        (Spalten 'sets' / 'default_sets' sind optional)
    """
    has_se_sets = _table_has_column(db, "session_entries", "sets")
    has_pe_sets = _table_has_column(db, "plan_exercises", "default_sets")

    se_sets_expr = "se.sets" if has_se_sets else "NULL"
    pe_sets_expr = "pe.default_sets" if has_pe_sets else "NULL"

    sql = f"""
        SELECT
            e.id   AS exercise_id,
            e.name AS name,
            COALESCE({se_sets_expr}, {pe_sets_expr}, 3)  AS sets,
            COALESCE(se.reps,      pe.default_reps,      10) AS reps,
            COALESCE(se.weight_kg, pe.default_weight_kg,  0) AS weight_kg,
            COALESCE(se.note,      pe.note,              '') AS note
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


def _upsert_entries(db: sqlite3.Connection, session_id: int, form: Dict[str, Any]) -> None:
    """
    Write one aggregate row per exercise into session_entries.
    Unterstützte Formnamen:
      A) ex[<id>][sets|reps|weight|note]
      B) flat: exercise_id + sets_<id>, reps_<id>, weight_<id>, note_<id>

    Besonderheiten:
      - Sätze 0..99 (0 = Übung ausgelassen -> kein Datensatz)
      - Spalte 'sets' ist optional: wird nur beschrieben, wenn vorhanden
    """
    # Parser (falls vorhanden) darf liefern; ansonsten Fallback
    try:
        from fitlog.services.record_parser import parse_exercises_form
        parsed = parse_exercises_form(form)  # Dict[int, Dict[str, Any]]
    except Exception:
        parsed = {}

    has_se_sets = _table_has_column(db, "session_entries", "sets")

    # Alle exercise_ids aus dem Formular
    exercise_ids = request.form.getlist("exercise_id")
    if not exercise_ids:
        # Versuche IDs aus Keys zu parsen: ex[<id>][...] oder <field>_<id>
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

        # Defaults
        sets_val: Optional[int] = None  # None = unbekannt / nicht gesetzt
        reps = 0
        weight = 0.0
        note = ""

        # Flache Form zuerst lesen
        if sets_key in form:
            try:
                sets_val = max(0, min(99, int(str(form[sets_key]).strip())))
            except ValueError:
                sets_val = 0

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

        # Parser-Werte (verschachtelte ex[<id>][...]) haben Priorität
        payload = parsed.get(ex_id, {})
        if "sets" in payload:
            try:
                sets_val = max(0, min(99, int(payload.get("sets", 0))))
            except Exception:
                sets_val = 0
        if "reps" in payload:
            try:
                reps = max(0, int(payload.get("reps", reps)))
            except Exception:
                reps = reps
        if "weight" in payload:
            try:
                weight = max(0.0, float(str(payload.get("weight", weight)).replace(",", ".")))
            except Exception:
                weight = weight
        if "note" in payload:
            note = str(payload.get("note", note) or "").strip()

        # Sätze==0 → Eintrag löschen (ausgelassen)
        if sets_val is not None and sets_val == 0:
            db.execute(
                "DELETE FROM session_entries WHERE session_id = ? AND exercise_id = ?",
                (session_id, ex_id),
            )
            continue

        # Dynamisches INSERT/UPSERT (mit optionaler Spalte 'sets')
        if has_se_sets:
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
            db.execute(sql, [session_id, ex_id, weight, reps,
                             (sets_val if sets_val is not None else 3),
                             note, _utcnow_sqlite()])
        else:
            sql = """
                INSERT INTO session_entries (session_id, exercise_id, weight_kg, reps, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, exercise_id) DO UPDATE SET
                  weight_kg = excluded.weight_kg,
                  reps      = excluded.reps,
                  note      = excluded.note,
                  created_at= excluded.created_at
            """
            db.execute(sql, [session_id, ex_id, weight, reps, note, _utcnow_sqlite()])


# ------------------------------
# Routes
# ------------------------------
@bp.get("/new", endpoint="new_session")
def new_session():
    """Neue Session starten – nur mit plan_id."""
    plan_id = request.args.get("plan_id", type=int)
    if not plan_id:
        flash("Bitte zuerst einen Trainingsplan auswählen.", "info")
        return redirect(url_for("index"))

    db = get_db()
    started_at = _utcnow_sqlite()
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
    """Trainingsdaten erfassen-Formular anzeigen (eine Zeile je Übung)."""
    db = get_db()
    sess = _load_session(db, session_id)
    items = _load_record_items(db, session_id)
    db.close()

    # started_at schön formatieren
    started_display = sess["started_at"]
    try:
        started_display = datetime.fromisoformat(started_display).strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        pass

    return render_template(
        "sessions/record.html",
        sess=sess,
        started_display=started_display,
        items=items,
        defaults={},
    )


@bp.post("/<int:session_id>/finish")
def finish_session(session_id: int):
    """Training speichern & beenden (→ Startseite zeigt korrekt „Letztes Training“)."""
    db = get_db()
    sess = _load_session(db, session_id)
    _upsert_entries(db, session_id, request.form)

    # Optional: Dauer in Minuten
    raw_minutes = request.form.get("duration_minutes_override") or request.form.get("duration_minutes")
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
        ended_at_iso = (start_dt + timedelta(minutes=mins)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (ended_at_iso, session_id))
    else:
        # klassischer „Training beenden“-Klick -> Ende jetzt, falls nicht schon gesetzt
        db.execute(
            "UPDATE sessions SET ended_at = COALESCE(ended_at, ?) WHERE id = ?",
            (_utcnow_sqlite(), session_id),
        )

    db.commit()
    db.close()
    flash("Training wurde gespeichert ✅", "success")
    return redirect(url_for("index"))


@bp.post("/<int:session_id>/abort")
def abort_session(session_id: int):
    """Training abbrechen – löscht Session und Einträge (keine ‚Letztes Training‘-Aktualisierung)."""
    db = get_db()
    _ = _load_session(db, session_id)
    db.execute("DELETE FROM session_entries WHERE session_id = ?", (session_id,))
    db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    db.commit()
    db.close()
    flash("Training abgebrochen.", "info")
    return redirect(url_for("index"))
