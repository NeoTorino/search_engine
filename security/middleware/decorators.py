"""
Security decorators for Flask endpoints
"""
import logging
from functools import wraps
from typing import Dict, Any, Optional
from flask import request, abort, current_app

from security.middleware.rate_limiting import apply_rate_limit
from security.middleware.request_validation import validate_request_security, validate_content_type
from security.monitoring.detection import detect_bot_behavior
from security.monitoring.logging import log_security_event
from security.core.main import get_search_params
from security.core.validators import check_request_security, security_validator, ValidationResult

security_logger = logging.getLogger('security')

def secure_endpoint(validation_config: Dict[str, Dict] = None,
                   auto_sanitize: bool = True,
                   block_on_threat: bool = True,
                   log_threats: bool = True):
    """
    Comprehensive security decorator for Flask endpoints

    Args:
        validation_config: Field-specific validation rules
        auto_sanitize: Automatically replace request data with sanitized versions
        block_on_threat: Block request if high/critical threats detected
        log_threats: Log security threats

    Example usage:
        @app.route('/search')
        @secure_endpoint({
            'q': {'type': 'search', 'max_length': 200},
            'country': {'type': 'filter', 'max_length': 50},
            'limit': {'type': 'general', 'max_length': 10}
        })
        def search():
            # Your endpoint logic here
            # request.args will contain sanitized data if auto_sanitize=True
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Perform comprehensive security check
            is_safe, sanitized_data = check_request_security(validation_config)

            # Log the security check results
            if log_threats and not is_safe:
                security_logger.warning(
                    "Security threats detected in request to %s from IP %s",
                    request.endpoint,
                    request.remote_addr
                )

            # Block request if critical threats detected
            if block_on_threat and not is_safe:
                # Check severity of threats
                has_critical_threats = False
                if hasattr(request, '_security_validation_results'):
                    has_critical_threats = any(
                        result.severity in ['HIGH', 'CRITICAL']
                        for result in request._security_validation_results.values()
                    )

                if has_critical_threats:
                    security_logger.error(
                        "Blocking request to %s due to critical security threats",
                        request.endpoint
                    )
                    abort(400)  # Bad Request

            # Auto-sanitize request data if enabled
            if auto_sanitize:
                _inject_sanitized_data(sanitized_data)

            # Store validation results for use in endpoint
            request._security_validation_results = getattr(request, '_security_validation_results', {})
            request._sanitized_data = sanitized_data
            request._is_request_safe = is_safe

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_single_input(input_name: str,
                         input_type: str = 'general',
                         max_length: int = 1000,
                         required: bool = False,
                         allow_html: bool = False):
    """
    Decorator to validate a single input parameter

    Example:
        @app.route('/user/<user_id>')
        @validate_single_input('user_id', 'general', max_length=50, required=True)
        def get_user(user_id):
            # user_id is now validated and sanitized
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get the input value
            value = None
            if input_name in request.args:
                value = request.args.get(input_name)
            elif request.is_json and request.get_json() and input_name in request.get_json():
                value = request.get_json()[input_name]
            elif input_name in request.form:
                value = request.form.get(input_name)
            elif input_name in kwargs:
                value = kwargs[input_name]

            # Check if required
            if required and not value:
                abort(400)  # Bad Request - missing required parameter

            if value:
                # Validate the input
                result = security_validator.validate_input(
                    value=value,
                    input_type=input_type,
                    max_length=max_length,
                    allow_html=allow_html
                )

                # Block if not valid
                if not result.is_valid:
                    security_logger.warning(
                        "Invalid input '%s' for parameter '%s': threats=%s severity=%s",
                        value, input_name, result.threats_detected, result.severity
                    )

                    if result.severity in ['HIGH', 'CRITICAL']:
                        abort(400)

                # Replace with sanitized value
                if input_name in kwargs:
                    kwargs[input_name] = result.sanitized_value

                # Store result for endpoint use
                if not hasattr(request, '_validation_results'):
                    request._validation_results = {}
                request._validation_results[input_name] = result

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def _inject_sanitized_data(sanitized_data: Dict[str, Any]):
    """Inject sanitized data into request object"""
    # This is a bit of a hack since Flask request objects are immutable
    # In practice, you'd access the sanitized data from request._sanitized_data
    pass

def get_sanitized_param(param_name: str, default: Any = None) -> Any:
    """
    Get sanitized parameter from current request

    Usage in your endpoint:
        query = get_sanitized_param('q', '')
        country = get_sanitized_param('country', [])
    """
    if hasattr(request, '_sanitized_data') and param_name in request._sanitized_data:
        return request._sanitized_data[param_name]
    return default

def get_validation_result(param_name: str) -> Optional[ValidationResult]:
    """Get validation result for a specific parameter"""
    if hasattr(request, '_security_validation_results'):
        return request._security_validation_results.get(param_name)
    return None

def is_request_safe() -> bool:
    """Check if current request passed all security validations"""
    return getattr(request, '_is_request_safe', True)

# Pre-defined validation configurations for common use cases
COMMON_VALIDATIONS = {
    'search_api': {
        'q': {'type': 'search', 'max_length': 200},
        'country': {'type': 'filter', 'max_length': 20},
        'organization': {'type': 'filter', 'max_length': 20},
        'source': {'type': 'filter', 'max_length': 20},
        'limit': {'type': 'general', 'max_length': 10},
        'offset': {'type': 'general', 'max_length': 10},
        'date_posted_days': {'type': 'general', 'max_length': 10}
    },
    'user_profile': {
        'name': {'type': 'general', 'max_length': 100},
        'email': {'type': 'email', 'max_length': 254},
        'bio': {'type': 'general', 'max_length': 500, 'allow_html': True}
    },
    'file_upload': {
        'filename': {'type': 'filename', 'max_length': 255},
        'description': {'type': 'general', 'max_length': 1000}
    }
}

# Quick decorators for common scenarios
def secure_search_endpoint():
    """Quick decorator for search endpoints"""
    return secure_endpoint(COMMON_VALIDATIONS['search_api'])

def secure_user_endpoint():
    """Quick decorator for user profile endpoints"""
    return secure_endpoint(COMMON_VALIDATIONS['user_profile'])

def secure_file_endpoint():
    """Quick decorator for file upload endpoints"""
    return secure_endpoint(COMMON_VALIDATIONS['file_upload'])

# Middleware class for Flask app
class SecurityMiddleware:
    """Flask middleware for automatic security validation"""

    def __init__(self, app=None, default_config=None):
        self.app = app
        self.default_config = default_config or {}
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        """Run before each request"""
        # Skip security checks for certain endpoints if needed
        if request.endpoint in getattr(current_app, 'SECURITY_SKIP_ENDPOINTS', []):
            return

        # Apply default security validation
        is_safe, sanitized_data = check_request_security(self.default_config)

        # Store results
        request._is_request_safe = is_safe
        request._sanitized_data = sanitized_data

        # Block unsafe requests if configured
        if not is_safe and getattr(current_app, 'SECURITY_BLOCK_UNSAFE', False):
            abort(400)

    def after_request(self, response):
        """Run after each request"""
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'

        return response


def comprehensive_security(endpoint_type='api'):
    """
    Comprehensive security decorator that combines multiple security checks
    This simplifies usage by combining common security patterns
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Bot detection
            if detect_bot_behavior():
                log_security_event('BOT_DETECTED', 'Suspicious bot behavior', 'WARNING')
                abort(429)

            # Apply rate limiting
            rate_limit_decorator = apply_rate_limit(endpoint_type)
            rate_limited_func = rate_limit_decorator(f)

            # Apply request validation
            validation_decorator = validate_request_security(endpoint_type)
            validated_func = validation_decorator(rate_limited_func)

            return validated_func(*args, **kwargs)
        return decorated_function
    return decorator

def secure_json_api(f):
    """
    Decorator for JSON API endpoints with comprehensive security
    Combines JSON validation, rate limiting, and security checks
    """
    @wraps(f)
    @comprehensive_security('api')
    @validate_content_type(['application/json'])
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def secure_search_api(f):
    """
    Decorator specifically for search endpoints
    Includes search-specific validation and rate limiting
    """
    @wraps(f)
    @comprehensive_security('search')
    def decorated_function(*args, **kwargs):
        # Add search-specific parameter extraction and validation
        try:
            search_params = get_search_params()
            g.search_params = search_params
        except Exception as e:
            log_security_event('SEARCH_PARAMS_ERROR', str(e), 'WARNING')
            abort(400)

        return f(*args, **kwargs)
    return decorated_function

def secure_upload_api(max_file_size=5*1024*1024):  # 5MB default
    """
    Decorator for file upload endpoints
    Includes file size validation and upload-specific security
    """
    def decorator(f):
        @wraps(f)
        @comprehensive_security('upload')
        @validate_content_type(['multipart/form-data'])
        def decorated_function(*args, **kwargs):
            # Validate file size
            if request.content_length and request.content_length > max_file_size:
                log_security_event(
                    'LARGE_UPLOAD',
                    f'Size: {request.content_length}, Max: {max_file_size}',
                    'WARNING'
                )
                abort(413)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def ip_whitelist(allowed_ips):
    """
    Decorator to restrict access to specific IP addresses
    Useful for admin or internal endpoints
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            if client_ip not in allowed_ips:
                log_security_event(
                    'IP_NOT_WHITELISTED',
                    f'IP: {client_ip}, Allowed: {allowed_ips}',
                    'HIGH'
                )
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_api_key(header_name='X-API-Key'):
    """
    Decorator to require API key authentication
    Reads valid API keys from security settings
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get(header_name)
            if not api_key:
                log_security_event('MISSING_API_KEY', f'Header: {header_name}', 'WARNING')
                abort(401)

            # Validate API key (implement your validation logic)
            valid_keys = security_settings.get_api_keys()
            if api_key not in valid_keys:
                log_security_event('INVALID_API_KEY', f'Key: {api_key[:8]}...', 'WARNING')
                abort(401)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_request_details(include_body=False):
    """
    Decorator to log detailed request information
    Useful for debugging and audit trails
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            details = {
                'method': request.method,
                'path': request.path,
                'args': dict(request.args),
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'headers': dict(request.headers)
            }

            if include_body and request.is_json:
                try:
                    details['body'] = request.get_json()
                except:
                    details['body'] = 'Invalid JSON'

            log_security_event('REQUEST_LOGGED', details, 'INFO')
            return f(*args, **kwargs)
        return decorated_function
    return decorator
