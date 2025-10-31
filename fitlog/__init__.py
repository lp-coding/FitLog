from flask import Flask
from .config import load_config
from .db import init_db
import os

def create_app() -> Flask:
    """App-Factory: erstellt und konfiguriert die Flask-Anwendung."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(load_config())

    # Sicherstellen, dass instance/ existiert
    os.makedirs(app.instance_path, exist_ok=True)

    # DB-Integration
    init_db(app)

    # Blueprints registrieren
    from .routes import plans, training, progress
    app.register_blueprint(plans.bp)
    app.register_blueprint(training.bp)
    app.register_blueprint(progress.bp)

    @app.route("/")
    def index():
        return "Welcome to FitLog!"

    return app
