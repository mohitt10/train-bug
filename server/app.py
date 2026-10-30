from uuid import uuid4
from flask import Flask, g, jsonify, request
from werkzeug.routing import IntegerConverter
from werkzeug.exceptions import NotFound

from config import Config
from db import execute_query
from auth import auth_bp
from content import content_bp
from content.responses import error_response
from users import users_bp


class SafeIntConverter(IntegerConverter):
    """Prevents database 32-bit integer overflow by rejecting out-of-range IDs with 404."""
    def to_python(self, value):
        val = super().to_python(value)
        if val > 2147483647 or val < 1:
            raise NotFound()
        return val


app = Flask(__name__)
app.config.from_object(Config)
app.url_map.converters["int"] = SafeIntConverter

app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(content_bp)


@app.before_request
def assign_request_id():
    g.request_id = str(uuid4())
    g.endpoint = f"{request.method} {request.url_rule.rule}" if request.url_rule else request.path


@app.after_request
def add_request_id_header(response):
    response.headers["X-Request-ID"] = getattr(g, "request_id", "")
    return response


@app.errorhandler(404)
def handle_404(err):
    return error_response("NOT_FOUND", "The requested resource was not found.", 404)


@app.errorhandler(405)
def handle_405(err):
    return error_response("METHOD_NOT_ALLOWED", "The method is not allowed for the requested URL.", 405)


@app.errorhandler(500)
def handle_500(err):
    app.logger.exception("Internal server error: %s", err)
    return error_response("INTERNAL_ERROR", "An unexpected server error occurred.", 500)


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
