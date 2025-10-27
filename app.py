"""
FitLog – Der Trainingsplantracker
---------------------------------
Flask-basierte Webanwendung zur Verwaltung von Trainingsplänen und Übungen.

Funktionen (aktuell implementiert):
- Datenbank-Initialisierung mit SQLAlchemy
- Beispiel-Routen für Startseite, Planübersicht und Plan-Erstellung
- Robuste SQLite-Integration mit automatischer Ordnererstellung
"""

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

# ------------------------------------------------------------
# Flask & Datenbank-Konfiguration
# ------------------------------------------------------------

# Flask-App mit instance-relative Pfad (enthält z. B. die SQLite-DB)
app = Flask(__name__, instance_relative_config=True)

# Stelle sicher, dass der "instance"-Ordner existiert (sonst kann SQLite nicht schreiben!)
os.makedirs(app.instance_path, exist_ok=True)

# Erstelle absoluten Pfad zur SQLite-Datenbank
db_path = os.path.join(app.instance_path, "fitlog.db")
db_uri = "sqlite:///" + db_path.replace("\\", "/")

# Flask-Konfiguration
app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "dev"  # später evtl. aus .env laden

# Datenbank-Objekt
db = SQLAlchemy(app)


# ------------------------------------------------------------
# Datenbank-Modelle
# ------------------------------------------------------------

class Trainingsplan(db.Model):
    __tablename__ = "trainingsplaene"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    # Beziehung zu Übungen
    uebungen = db.relationship("Uebung", backref="trainingsplan", lazy=True)

    def __repr__(self):
        return f"<Trainingsplan {self.name}>"


class Uebung(db.Model):
    __tablename__ = "uebungen"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    standardgewicht = db.Column(db.Float, nullable=True)

    plan_id = db.Column(db.Integer, db.ForeignKey("trainingsplaene.id"), nullable=False)

    def __repr__(self):
        return f"<Uebung {self.name} ({self.standardgewicht} kg)>"


# ------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------

def init_db():
    """Erzeugt die Datenbanktabellen, falls sie nicht existieren."""
    with app.app_context():
        if not os.path.exists(db_path):
            print(f"[FitLog] Neue SQLite-DB wird angelegt unter:\n → {db_path}")
        db.create_all()
        print("[FitLog] Datenbank initialisiert.")


# ------------------------------------------------------------
# Routen
# ------------------------------------------------------------

@app.route("/")
def index():
    """Startseite"""
    return render_template("index.html") if os.path.exists("templates/index.html") else "<h1>Willkommen bei FitLog!</h1><p><a href='/plaene'>→ Zu den Trainingsplänen</a></p>"


@app.route("/plaene")
def plaene():
    """Zeigt alle vorhandenen Trainingspläne."""
    plaene = Trainingsplan.query.all()
    html = "<h1>Trainingspläne</h1><ul>"
    for p in plaene:
        html += f"<li>{p.name}</li>"
    html += "</ul><a href='/neu'>Neuen Plan anlegen</a>"
    return html


@app.route("/neu", methods=["GET", "POST"])
def neuer_plan():
    """Ermöglicht das Anlegen eines neuen Trainingsplans."""
    if request.method == "POST":
        name = request.form.get("name")
        if name:
            neuer_plan = Trainingsplan(name=name)
            db.session.add(neuer_plan)
            db.session.commit()
            return redirect(url_for("plaene"))
        else:
            return "<p>Bitte Namen eingeben!</p>"
    return '''
        <h1>Neuen Trainingsplan anlegen</h1>
        <form method="post">
            <input type="text" name="name" placeholder="Planname">
            <input type="submit" value="Erstellen">
        </form>
        <a href="/plaene">Zurück</a>
    '''


# ------------------------------------------------------------
# App-Startpunkt
# ------------------------------------------------------------

if __name__ == "__main__":
    init_db()  # DB anlegen, falls nicht vorhanden
    print(f"[FitLog] Läuft mit Datenbank: {db_path}")
    app.run(debug=True)
