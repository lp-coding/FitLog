# fitlog/__init__.py
from __future__ import annotations
from pathlib import Path
from flask import Flask
from .db import close_db, get_db

def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # Default-Config; kann von instance/config.py überschrieben werden
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=str(Path(app.instance_path) / "fitlog.db"),
    )
    # Optional: überschreiben aus instance/config.py
    app.config.from_pyfile("config.py", silent=True)

    if test_config:
        app.config.update(test_config)

    # Stelle sicher, dass instance/ existiert
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    # DB am Request-Ende schließen
    app.teardown_appcontext(close_db)

    # --- Optional: kleines Health-Endpoint
    @app.get("/health")
    def health():
        # Testet, ob DB erreichbar ist
        _ = get_db()
        return {"status": "ok"}

    # TODO: Blueprints registrieren, sobald vorhanden
    # from .blueprints.training import bp as training_bp
    # app.register_blueprint(training_bp)

    # --- Optional: CLI-Kommando zum (Re-)Initialisieren
    @app.cli.command("init-db")
    def init_db_command():
        """(Re)initialisiert die Datenbank aus instance/001_init.sql."""
        import sqlite3
        sql_path = Path(app.instance_path) / "001_init.sql"
        db_path = Path(app.config["DATABASE"])

        with sqlite3.connect(db_path) as con, open(sql_path, "r", encoding="utf-8") as f:
            con.executescript(f.read())
            con.commit()
        print("✅ DB init done.")

    return app
