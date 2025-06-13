from werkzeug.middleware.proxy_fix import ProxyFix
from middleware.secure_headers import apply_secure_headers
from routes.errors import register_error_handlers
from filters.custom_filters import register_filters
from .extensions import get_extensions

def setup_middleware(app):
    """Setup all middleware for the application"""

    # Setup proxy handling for production deployment
    setup_proxy_fix(app)

    # Register custom filters
    register_filters(app)

    # Setup error handlers
    setup_error_handlers(app)

    # Setup security headers
    setup_security_headers(app)

    app.logger.info("Middleware setup completed")

def setup_proxy_fix(app):
    """Setup proxy handling for reverse proxy deployments"""
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_prefix=1
    )
    app.logger.debug("Proxy fix middleware configured")

def setup_error_handlers(app):
    """Setup error handlers with security enforcer"""
    extensions = get_extensions()
    redis_client = extensions.get('redis_client')

    # We need to import SecurityEnforcer here to avoid circular imports
    from security_config import SecurityEnforcer
    security_enforcer = SecurityEnforcer(redis_client)

    register_error_handlers(app, security_enforcer)
    app.logger.debug("Error handlers registered")

def setup_security_headers(app):
    """Setup security headers middleware"""
    app.after_request(apply_secure_headers)
    app.logger.debug("Security headers middleware configured")
