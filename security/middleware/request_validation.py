"""
Request validation middleware
Provides comprehensive request validation using core validators and settings
"""

import logging
from functools import wraps
from flask import request, abort, g
from security.core.validators import security_validator, ValidationResult
from security.settings import security_settings
from security.monitoring.logging import log_security_event

logger = logging.getLogger(__name__)

def validate_request_security(validation_config=None):
    """
    Comprehensive request security validation
    Uses configuration from settings.py
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip validation for whitelisted endpoints
            if security_settings.should_skip_security(request.endpoint):
                return f(*args, **kwargs)

            # Get validation config
            config = validation_config or security_settings.get_validation_config('default')

            # Validate request size
            max_size = config.get('max_request_size', 1024 * 1024)  # 1MB default
            if request.content_length and request.content_length > max_size:
                log_security_event(
                    'LARGE_REQUEST',
                    f'Size: {request.content_length}, Max: {max_size}',
                    'WARNING'
                )
                abort(413)

            # Validate JSON requests
            if request.is_json:
                try:
                    data = request.get_json(force=True)
                    if not _validate_json_structure(data, config):
                        log_security_event('MALICIOUS_JSON', 'Dangerous JSON detected', 'WARNING')
                        abort(400)
                except Exception as e:
                    log_security_event('INVALID_JSON', str(e), 'WARNING')
                    abort(400)

            # Validate query parameters
            if request.args:
                validation_result = _validate_query_params(request.args, config)
                if not validation_result.is_safe:
                    log_security_event(
                        'MALICIOUS_PARAMS',
                        f'Threats: {validation_result.threats}',
                        validation_result.severity
                    )
                    if validation_result.severity == 'HIGH':
                        abort(400)

            # Store validation results for use in the request
            g.security_validation = {
                'config': config,
                'validated': True
            }

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def _validate_json_structure(data, config, max_depth=10, current_depth=0):
    """Validate JSON structure for security threats"""
    if current_depth > max_depth:
        return False

    max_json_size = config.get('max_json_size', 50000)
    max_keys = config.get('max_json_keys', 100)
    max_array_size = config.get('max_json_array_size', 1000)

    if isinstance(data, dict):
        if len(data) > max_keys:
            return False

        # Check total size
        if len(str(data)) > max_json_size:
            return False

        for key, value in data.items():
            # Validate key
            if isinstance(key, str):
                result = security_validator.validate_input(key, 'text', 100, False)
                if not result.is_safe:
                    return False

            # Recursively validate value
            if not _validate_json_structure(value, config, max_depth, current_depth + 1):
                return False

    elif isinstance(data, list):
        if len(data) > max_array_size:
            return False
        for item in data:
            if not _validate_json_structure(item, config, max_depth, current_depth + 1):
                return False

    elif isinstance(data, str):
        if len(data) > max_json_size:
            return False
        result = security_validator.validate_input(data, 'text', len(data), False)
        if not result.is_safe:
            return False

    return True

def _validate_query_params(args, config):
    """Validate query parameters"""
    combined_result = ValidationResult()

    for key, values in args.items():
        # Validate parameter name
        key_result = security_validator.validate_input(key, 'text', 100, False)
        combined_result = combined_result.combine(key_result)

        # Validate parameter values
        if isinstance(values, list):
            for value in values:
                value_result = security_validator.validate_input(value, 'text', 1000, False)
                combined_result = combined_result.combine(value_result)
        else:
            value_result = security_validator.validate_input(values, 'text', 1000, False)
            combined_result = combined_result.combine(value_result)

    return combined_result

def validate_content_type(allowed_types):
    """Validate request content type"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            content_type = request.content_type or ''

            if content_type and not any(ct in content_type for ct in allowed_types):
                log_security_event(
                    'INVALID_CONTENT_TYPE',
                    f'Content-Type: {content_type}, Allowed: {allowed_types}',
                    'WARNING'
                )
                abort(415)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_request_method(allowed_methods):
    """Validate HTTP request method"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method not in allowed_methods:
                log_security_event(
                    'INVALID_METHOD',
                    f'Method: {request.method}, Allowed: {allowed_methods}',
                    'WARNING'
                )
                abort(405)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Convenience decorators for common validation scenarios
def secure_api_request(f):
    """Secure API request with standard validation"""
    return validate_request_security('api')(f)

def secure_search_request(f):
    """Secure search request with search-specific validation"""
    return validate_request_security('search')(f)

def secure_upload_request(f):
    """Secure upload request with upload-specific validation"""
    return validate_request_security('upload')(f)
