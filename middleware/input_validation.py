from functools import wraps
from flask import request, jsonify, abort

def validate_request_size(max_size=1024*1024):  # 1MB default
    """Validate request size to prevent DoS"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.content_length and request.content_length > max_size:
                log_security_event("LARGE_REQUEST", f"Size: {request.content_length}")
                abort(413)  # Request Entity Too Large
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_json_request(f):
    """Validate JSON requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.is_json:
            try:
                # Limit JSON depth and size
                data = request.get_json(force=True)
                if isinstance(data, dict) and len(str(data)) > 10000:
                    log_security_event("LARGE_JSON", "JSON too large")
                    abort(400)
            except Exception as e:
                log_security_event("INVALID_JSON", str(e))
                abort(400)
        return f(*args, **kwargs)
    return decorated_function