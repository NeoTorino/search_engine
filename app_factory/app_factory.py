import os
import warnings
import urllib3

os.environ['PYTHONWARNINGS'] = 'ignore:Unverified HTTPS request'
urllib3.disable_warnings()
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

from flask import Flask
from dotenv import load_dotenv

from config.logging import setup_logging

from filters.custom_filters import register_filters

from .extensions import init_extensions
from .middleware_setup import setup_middleware
from .security_setup import setup_security
from .route_setup import register_blueprints

# Load environment
load_dotenv(".env")

def create_app(config_class=None):
    """Flask application factory"""

    log_level = config_class.LOG_LEVEL if config_class else 'INFO'
    setup_logging(log_level=log_level)

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

    return app
