"""
Standard response envelope, per API.md.

Success:
    {"success": true, "data": {...}, "meta": {...}}   # meta optional

Error:
    {"success": false, "error": {"code": ..., "message": ..., "details": [...]}}
"""
from flask import jsonify


def success_response(data=None, meta=None, status_code=200):
    body = {"success": True, "data": data if data is not None else {}}
    if meta is not None:
        body["meta"] = meta
    return jsonify(body), status_code


def error_response(code: str, message: str, status_code: int, details=None):
    body = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details is not None:
        body["error"]["details"] = details
    return jsonify(body), status_code
