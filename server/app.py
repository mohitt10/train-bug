from uuid import uuid4
from flask import Flask, g, jsonify
from config import Config
from db import execute_query
from content import content_bp


app = Flask(__name__)
app.config.from_object(Config)
app.register_blueprint(content_bp)


@app.before_request
def assign_request_id():
    g.request_id = str(uuid4())


@app.after_request
def add_request_id_header(response):
    response.headers["X-Request-ID"] = g.request_id
    return response


@app.get("/api/health")
def health():
    return jsonify(
        status="ok",
        service="social-media-api",
    )


@app.get("/api/health/db")
def database_health():
    try:
        result = execute_query(
            "SELECT 1",
            fetch="one",
            action="database_health_check",
        )

        if result["rows"] != (1,):
            raise RuntimeError("Unexpected database health-check result.")

        return jsonify(
            status="ok",
            database="connected",
        )

    except Exception:
        app.logger.error("Database health check failed.")

        return jsonify(
            status="error",
            database="unavailable",
        ), 503
