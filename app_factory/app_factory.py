import os
import secrets
import urllib3
from datetime import datetime
from flask import Flask, request, redirect, g
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

from .extensions import init_extensions
from .middleware_setup import setup_middleware
from .security_setup import setup_security
from .route_setup import register_blueprints
from filters.custom_filters import register_filters
from utils.monitoring import security_monitor

# Load environment
load_dotenv(".env")

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_app(config_class=None):
    """Flask application factory"""

    # Setup enhanced logging first
    security_logger = security_monitor.logger

    # Create Flask app
    app = Flask(__name__)

    # Setup proxy handling for production deployment
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_prefix=1
    )

    # Load configuration
    if config_class:
        app.config.from_object(config_class)
        # Validate secret key
        config_class.validate_secret_key()
    else:
        # Default configuration if none provided
        from config import get_config
        config_class = get_config()
        app.config.from_object(config_class)
        config_class.validate_secret_key()

    # Initialize extensions
    init_extensions(app)

    # Setup security
    setup_security(app)

    # Setup middleware
    setup_middleware(app)

    # Setup filters
    register_filters(app)

    # Register blueprints
    register_blueprints(app)

    # Setup request hooks
    _setup_request_hooks(app)

    # Setup context processors
    _setup_context_processors(app)

    security_logger.info("Flask application created successfully")

    return app

def _setup_request_hooks(app):
    """Setup request hooks for security and monitoring"""

    @app.before_request
    def before_request_security():
        # Force HTTPS redirect
        if os.getenv('FORCE_HTTPS', 'True').lower() == 'true':
            if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
                if request.endpoint not in ['main.health_check']:
                    return redirect(request.url.replace('http://', 'https://'), code=301)

        # Set CSP nonce
        g.csp_nonce = secrets.token_urlsafe(16)

        # Log request for monitoring (if sensitive endpoint)
        from security_config import SecurityConfig, log_security_event
        if request.endpoint in SecurityConfig.SENSITIVE_ENDPOINTS:
            log_security_event("SENSITIVE_ENDPOINT_ACCESS", f"Endpoint: {request.endpoint}")

def _setup_context_processors(app):
    """Setup template context processors"""

    @app.context_processor
    def inject_security_context():
        """Inject security context into templates"""
        return {
            'nonce': getattr(g, 'csp_nonce', ''),
            'year': datetime.utcnow().year,
            'is_secure': request.is_secure,
            'scheme': request.scheme
        }
