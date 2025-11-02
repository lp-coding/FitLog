from pathlib import Path
from flask import Flask

def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=str(Path(app.instance_path) / "fitlog.db"),
    )
    app.config.from_pyfile("config.py", silent=True)

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    # ⚠️ Import hier (nicht oben auf Modulebene)!
    from .db import close_db, get_db
    app.teardown_appcontext(close_db)

    @app.get("/health")
    def health():
        _ = get_db()
        return {"status": "ok"}

    # Blueprints registrieren
    from .blueprints.plans import bp as plans_bp
    app.register_blueprint(plans_bp)

    @app.cli.command("init-db")
    def init_db_command():
        import sqlite3
        sql_path = Path(app.instance_path) / "001_init.sql"
        db_path = Path(app.config["DATABASE"])
        with sqlite3.connect(db_path) as con, open(sql_path, "r", encoding="utf-8") as f:
            con.executescript(f.read())
            con.commit()
        print("✅ DB init done.")

    return app
