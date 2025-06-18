import os
import urllib3
from flask import Flask
from dotenv import load_dotenv

from filters.custom_filters import register_filters
from security.monitoring.logging import security_monitor

from .extensions import init_extensions
from .middleware_setup import setup_middleware
from .security_setup import setup_security
from .route_setup import register_blueprints

# Load environment
load_dotenv(".env")

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_app(config_class=None):
    """Flask application factory"""

    # Setup enhanced logging first
    security_logger = security_monitor.logger

    # Get the project root directory (one level up from app_factory)
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    # Create Flask app with explicit template and static folder paths
    app = Flask(__name__,
                template_folder=os.path.join(basedir, 'templates'),
                static_folder=os.path.join(basedir, 'static'))

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

    # Setup middleware (includes ProxyFix)
    setup_middleware(app)

    # Setup filters
    register_filters(app)

    # Register blueprints
    register_blueprints(app)

    security_logger.info("Flask application created successfully")

    return app