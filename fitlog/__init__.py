from pathlib import Path
from flask import Flask, render_template


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # Basis-Konfiguration
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=str(Path(app.instance_path) / "fitlog.db"),
    )

    # Test-Config überschreibt alles (z. B. für Tests)
    if test_config:
        app.config.update(test_config)

    # Instance-Ordner sicherstellen
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    # DB-Initialisierung / Teardown
    from .db import close_db, get_db
    app.teardown_appcontext(close_db)

    # Healthcheck
    @app.get("/health")
    def health():
        _ = get_db()
        return {"status": "ok"}

    # Startseite
    @app.get("/")
    def index():
        db = get_db()

        # Nur aktive Pläne anzeigen
        plans = db.execute(
            """
            SELECT id, name
              FROM training_plans
             WHERE deleted_at IS NULL
             ORDER BY name
            """
        ).fetchall()

        # Zuletzt abgeschlossene oder gestartete Session
        from fitlog.services.last_session import get_last_session
        last_session = get_last_session(db)

        return render_template("index.html", plans=plans, last_session=last_session)

    # Blueprints registrieren
    from .blueprints.plans import bp as plans_bp
    app.register_blueprint(plans_bp)

    from .blueprints.sessions import bp as sessions_bp
    app.register_blueprint(sessions_bp)

    from fitlog.routes.progress import progress_bp
    app.register_blueprint(progress_bp)

    return app
