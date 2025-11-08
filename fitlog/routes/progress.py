# fitlog/routes/progress.py
"""
FitLog – Fortschritt (Matplotlib-Charts)

Seitenfluss:
- /progress                  -> Diagrammauswahl (nur Dropdown + X + Zurück)
- /progress/plan             -> Balkendiagramm, Dropdown "Trainingsplan", Export, Zurück, X
- /progress/exercise         -> Liniendiagramm, Dropdown "Übung", Export, Zurück, X

Bild-Endpunkte (PNG + Download):
- /progress/plan_chart.png?plan_id=...
- /progress/exercise_chart.png?exercise_id=...
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import List, Tuple, Optional

from flask import (
    Blueprint, render_template, request, redirect, url_for, send_file, flash
)

import matplotlib
matplotlib.use("Agg")  # serverseitiges Rendering
import matplotlib.pyplot as plt

# Passe den Import ggf. an dein Projekt an:
from fitlog.db import get_db

bp = Blueprint("progress", __name__, url_prefix="/progress")


# ---------------------------
# Daten-Helper
# ---------------------------

def fetch_plans() -> List[Tuple[int, str]]:
    """Alle aktiven (nicht soft-gelöschten) Trainingspläne als (id, name)."""
    db = get_db()
    rows = db.execute(
        """
        SELECT id, name
        FROM training_plans
        WHERE deleted_at IS NULL
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()
    return [(r["id"], r["name"]) for r in rows]


def fetch_exercises() -> List[Tuple[int, str]]:
    """Alle Übungen als (id, name) alphabetisch."""
    db = get_db()
    rows = db.execute(
        "SELECT id, name FROM exercises ORDER BY name COLLATE NOCASE ASC"
    ).fetchall()
    return [(r["id"], r["name"]) for r in rows]


def fetch_plan_current_weights(plan_id: int) -> List[Tuple[str, float]]:
    """
    Für einen Plan: (Übungsname, letztes Gewicht) anhand des jüngsten Eintrags je Übung.
    Übungen ohne Einträge werden ausgeblendet, damit das Chart übersichtlich bleibt.
    """
    db = get_db()
    rows = db.execute(
        """
        WITH latest_entries AS (
            SELECT
                se.exercise_id,
                se.weight_kg,
                s.ended_at,
                ROW_NUMBER() OVER (PARTITION BY se.exercise_id ORDER BY s.ended_at DESC, s.id DESC) AS rn
            FROM session_entries se
            JOIN sessions s        ON s.id = se.session_id
            JOIN plan_exercises pe ON pe.exercise_id = se.exercise_id AND pe.plan_id = s.plan_id
            WHERE s.plan_id = ?
        )
        SELECT e.name AS exercise_name, le.weight_kg
        FROM latest_entries le
        JOIN exercises e ON e.id = le.exercise_id
        WHERE le.rn = 1 AND le.weight_kg IS NOT NULL
        ORDER BY e.name COLLATE NOCASE ASC
        """,
        (plan_id,),
    ).fetchall()
    return [(r["exercise_name"], float(r["weight_kg"])) for r in rows]


def fetch_exercise_timeseries(exercise_id: int) -> List[Tuple[datetime, float]]:
    """Zeitreihe (Zeitstempel, Gewicht) über alle Sessions zu einer Übung."""
    db = get_db()
    rows = db.execute(
        """
        SELECT s.ended_at AS ts, se.weight_kg
        FROM session_entries se
        JOIN sessions s ON s.id = se.session_id
        WHERE se.exercise_id = ? AND se.weight_kg IS NOT NULL
        ORDER BY s.ended_at ASC, s.id ASC
        """,
        (exercise_id,),
    ).fetchall()
    points: List[Tuple[datetime, float]] = []
    for r in rows:
        ts = r["ts"]
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                pass
        points.append((ts, float(r["weight_kg"])))
    return points


# ---------------------------
# Seiten
# ---------------------------

@bp.get("/")
def select_page():
    """
    Diagrammauswahl (Mockup 1).
    Wenn ?type=exercise|plan übergeben wird, leiten wir direkt auf die passende Seite.
    """
    diag_type = request.args.get("type")
    if diag_type == "plan":
        return redirect(url_for("progress.plan_page"))
    if diag_type == "exercise":
        return redirect(url_for("progress.exercise_page"))
    return render_template("progress_select.html")


@bp.get("/plan")
def plan_page():
    """
    Seite für Balkendiagramm (Mockup 2).
    - Dropdown 'Trainingsplan'
    - Export-Button (lädt PNG)
    - Bild <img> nur, wenn plan_id gesetzt ist
    """
    plans = fetch_plans()
    selected_plan = request.args.get("plan_id", type=int)
    return render_template(
        "progress_plan.html",
        plans=plans,
        selected_plan=selected_plan,
    )


@bp.get("/exercise")
def exercise_page():
    """
    Seite für Liniendiagramm (Mockup 3).
    - Dropdown 'Übung'
    - Export-Button (lädt PNG)
    - Bild <img> nur, wenn exercise_id gesetzt ist
    """
    exercises = fetch_exercises()
    selected_exercise = request.args.get("exercise_id", type=int)
    return render_template(
        "progress_exercise.html",
        exercises=exercises,
        selected_exercise=selected_exercise,
    )


# ---------------------------
# PNG-Endpunkte (Export)
# ---------------------------

@bp.get("/plan_chart.png")
def plan_chart_png():
    """PNG-Balkendiagramm für aktuellen Leistungsstand im Plan."""
    plan_id = request.args.get("plan_id", type=int)
    if not plan_id:
        flash("Kein Trainingsplan ausgewählt.")
        return redirect(url_for("progress.plan_page"))

    data = fetch_plan_current_weights(plan_id)

    fig, ax = plt.subplots(figsize=(7.5, 4.5), layout="constrained")
    if data:
        names = [n for n, _ in data]
        weights = [w for _, w in data]
        ax.bar(names, weights)
        ax.set_ylabel("Gewicht [kg]")
        ax.set_title("Aktueller Leistungsstand (letzter Eintrag je Übung)")
        ax.set_xticklabels(names, rotation=20, ha="right")
        ax.grid(axis="y", alpha=0.3)
    else:
        ax.text(0.5, 0.5, "Keine Daten vorhanden.", ha="center", va="center", fontsize=12)
        ax.axis("off")

    out = BytesIO()
    fig.savefig(out, format="png", dpi=150)
    plt.close(fig)
    out.seek(0)

    filename = f"plan_progress_{plan_id}.png"
    as_attachment = bool(request.args.get("download"))
    return send_file(out, mimetype="image/png", download_name=filename, as_attachment=as_attachment)


@bp.get("/exercise_chart.png")
def exercise_chart_png():
    """PNG-Liniendiagramm für Übungsentwicklung über Zeit."""
    exercise_id = request.args.get("exercise_id", type=int)
    if not exercise_id:
        flash("Keine Übung ausgewählt.")
        return redirect(url_for("progress.exercise_page"))

    # Name für Titel
    exercise_map = dict(fetch_exercises())
    exercise_name = exercise_map.get(exercise_id, f"Übung {exercise_id}")

    points = fetch_exercise_timeseries(exercise_id)

    fig, ax = plt.subplots(figsize=(7.5, 4.5), layout="constrained")
    if points:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        ax.plot(xs, ys, marker="o")
        ax.set_ylabel("Gewicht [kg]")
        ax.set_title(f"Leistung über Zeit – {exercise_name}")
        ax.grid(alpha=0.3)
    else:
        ax.text(0.5, 0.5, "Keine Daten vorhanden.", ha="center", va="center", fontsize=12)
        ax.axis("off")

    out = BytesIO()
    fig.savefig(out, format="png", dpi=150)
    plt.close(fig)
    out.seek(0)

    filename = f"exercise_progress_{exercise_id}.png"
    as_attachment = bool(request.args.get("download"))
    return send_file(out, mimetype="image/png", download_name=filename, as_attachment=as_attachment)
