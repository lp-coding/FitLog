from flask import Flask, render_template, url_for, redirect

app = Flask(__name__)
app.config["DEBUG"] = True  # Auto-Reload der Templates

# --- FAKE-DATEN statt DB (nur für Mockup) ---
PLANS = [
    {"id": 1, "name": "Push/Pull/Beine"},
    {"id": 2, "name": "Oberkörper/Unterkörper"},
    {"id": 3, "name": "Ganzkörper"},
]

PLAN_EXERCISES = {
    1: [  # Plan 1
        {"id": 101, "name": "Bankdrücken", "sets": 3, "reps": 10, "weight": 60, "note": ""},
        {"id": 102, "name": "Kniebeugen", "sets": 3, "reps": 8, "weight": 80, "note": ""},
    ],
    2: [
        {"id": 201, "name": "Latzug", "sets": 3, "reps": 10, "weight": 50, "note": ""},
    ],
    3: [
        {"id": 301, "name": "Butterfly", "sets": 3, "reps": 12, "weight": 20, "note": ""},
    ],
}

# --- ROUTES ---
@app.route("/")
def index():
    return render_template("index.html", plans=PLANS)

@app.route("/plan/<int:plan_id>")
def plan_view(plan_id: int):
    plan = next((p for p in PLANS if p["id"] == plan_id), None)
    exercises = PLAN_EXERCISES.get(plan_id, [])
    return render_template("plan_view.html", plan=plan, exercises=exercises)

@app.route("/plan/new")
def plan_new():
    return render_template("plan_new.html")

@app.route("/plan/<int:plan_id>/edit")
def plan_edit(plan_id: int):
    plan = next((p for p in PLANS if p["id"] == plan_id), None)
    exercises = PLAN_EXERCISES.get(plan_id, [])
    return render_template("plan_edit.html", plan=plan, exercises=exercises)

@app.route("/training/<int:plan_id>/<int:exercise_id>")
def training(plan_id: int, exercise_id: int):
    # Platzhalter: Zeige Formular für genau diese Übung des Plans
    plan = next((p for p in PLANS if p["id"] == plan_id), None)
    exercise = None
    for ex in PLAN_EXERCISES.get(plan_id, []):
        if ex["id"] == exercise_id:
            exercise = ex
            break
    return render_template("training.html", plan=plan, exercise=exercise)

if __name__ == "__main__":
    app.run()
