from pathlib import Path
from flask import Flask

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

    from .blueprints.plans import bp as plans_bp
    app.register_blueprint(plans_bp)

    return app
