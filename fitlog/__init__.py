from pathlib import Path
from flask import Flask, render_template

def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY="dev",
    )

    # Optionale Instanz-Config (wenn vorhanden)
    app.config.from_pyfile("config.py", silent=True)

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    from .db import close_db, get_db
    app.teardown_appcontext(close_db)

    @app.get("/health")
    def health():
        _ = get_db()
        return {"status": "ok"}

    @app.get("/")
    def index():
        # Startseite anzeigen
        from .db import get_db
        db = get_db()

        plans = db.execute("SELECT id, name FROM training_plans ORDER BY name").fetchall()
        last_session = db.execute(
            """
            SELECT s.id, s.started_at, s.ended_at, p.name AS plan_name
            FROM sessions s
            JOIN training_plans p ON p.id = s.plan_id
            ORDER BY COALESCE(s.ended_at, s.started_at) DESC LIMIT 1
            """
        ).fetchone()
        return render_template("index.html", plans=plans, last_session=last_session)

    from .blueprints.plans import bp as plans_bp
    app.register_blueprint(plans_bp)

    return app
