import secrets
from flask import g, request, redirect
from security_config import SecurityEnforcer, create_security_middleware, log_security_event
from .extensions import get_extensions

def setup_security(app):
    """Setup all security measures for the application"""
    extensions = get_extensions()
    redis_client = extensions.get('redis_client')

    # Initialize security enforcer
    security_enforcer = SecurityEnforcer(redis_client)

    # Setup security middleware
    create_security_middleware(app, security_enforcer)

    # Setup request hooks
    setup_request_hooks(app)

    # Setup context processors
    setup_context_processors(app)

    # Setup rate limiting rules
    setup_rate_limiting(app)

    app.logger.info("Security setup completed")
    return security_enforcer

def setup_request_hooks(app):
    """Setup before/after request hooks for security"""

    @app.before_request
    def before_request_security():
        # Force HTTPS redirect
        if app.config.get('FORCE_HTTPS', False):
            if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
                if request.endpoint not in ['main.health_check']:
                    return redirect(request.url.replace('http://', 'https://'), code=301)

        # Set CSP nonce
        g.csp_nonce = secrets.token_urlsafe(16)

        # Log sensitive endpoint access
        sensitive_endpoints = app.config.get('SENSITIVE_ENDPOINTS', [])
        if request.endpoint in sensitive_endpoints:
            log_security_event("SENSITIVE_ENDPOINT_ACCESS", f"Endpoint: {request.endpoint}")

def setup_context_processors(app):
    """Setup template context processors"""

    @app.context_processor
    def inject_security_context():
        """Inject security context into templates"""
        from datetime import datetime
        return {
            'nonce': getattr(g, 'csp_nonce', ''),
            'year': datetime.utcnow().year,
            'is_secure': request.is_secure,
            'scheme': request.scheme
        }

def setup_rate_limiting(app):
    """Setup rate limiting rules for different endpoints"""
    extensions = get_extensions()
    limiter = extensions.get('limiter')

    if not limiter:
        app.logger.warning("Rate limiter not available, skipping rate limit setup")
        return

    rate_limits = app.config.get('RATE_LIMITS', {})

    # Search endpoint rate limiting
    if 'search' in rate_limits:
        @limiter.limit(rate_limits['search'][2])  # Most restrictive
        def search_rate_limit():
            return request.endpoint == 'main.search_results'

    # API endpoint rate limiting
    if 'api' in rate_limits:
        @limiter.limit(rate_limits['api'][2])
        def api_rate_limit():
            return request.endpoint and request.endpoint.startswith('main.api.')

    app.logger.info("Rate limiting rules configured")
