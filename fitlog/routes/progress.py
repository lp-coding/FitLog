from flask import Blueprint, render_template, send_file, request
import io
import matplotlib
matplotlib.use("Agg")  # Headless-Backend
import matplotlib.pyplot as plt
from ..models import session as session_model, plan as plan_model

bp = Blueprint("progress", __name__, url_prefix="/progress")

@bp.route("/<int:plan_id>")
def plan_progress(plan_id: int):
    """Seite mit Diagrammen: Balken (Plan) + Auswahl für Übungslinie."""
    plan_data = plan_model.get_plan(plan_id)
    return render_template("progress.html", plan=plan_data)

@bp.route("/<int:plan_id>/bar.png")
def bar_chart(plan_id: int):
    """Erzeugt ein Balkendiagramm der aktuellen Gewichte je Übung (PNG)."""
    data = session_model.get_latest_weights_by_plan(plan_id)
    names = [d["name"] for d in data]
    weights = [d["weight"] for d in data]

    fig = plt.figure()
    plt.bar(names, weights)
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Gewicht (kg)")
    plt.title("Aktuelle Gewichte pro Übung")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@bp.route("/exercise_line.png")
def exercise_line():
    """Liniendiagramm des Gewichtsverlaufs für eine Übung (exercise_id als Query-Param)."""
    exercise_id = int(request.args.get("exercise_id"))
    data = session_model.get_weight_progress(exercise_id)
    xs = [d["ts"] for d in data]
    ys = [d["weight"] for d in data]

    fig = plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Gewicht (kg)")
    plt.title("Gewichtsverlauf")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")
