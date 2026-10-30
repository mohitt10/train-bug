from flask import jsonify


def error_response(code: str, message: str, status: int = 400):
    """
    Standard error response matching Phase 3 and docs/api-conventions.md:
    {
        "status": "error",
        "error": {
            "code": code,
            "message": message
        }
    }
    """
    return jsonify({
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        },
    }), status
