from flask import Flask, jsonify

def create_app():
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok"}), 200

    return app
