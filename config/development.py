import os
from .base import BaseConfig

class DevelopmentConfig(BaseConfig):
    """Development configuration"""

    # Debug settings
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = False

    # Security settings (relaxed for development)
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    SESSION_COOKIE_SAMESITE = 'Lax'
    PREFERRED_URL_SCHEME = 'https' if BaseConfig.DEV_HTTPS else 'http'

    # Development server settings
    FLASK_HOST = os.getenv('FLASK_HOST', '127.0.0.1')  # Localhost only

    # Logging
    LOG_LEVEL = 'DEBUG'

    @classmethod
    def get_cert_paths(cls):
        """Get development certificate paths"""
        return {
            'cert_path': os.getenv('DEV_CERT_PATH', './certs/development/dev.crt'),
            'key_path': os.getenv('DEV_KEY_PATH', './certs/development/dev.key')
        }

    @classmethod
    def init_app(cls, app):
        """Initialize development-specific settings"""
        # Validate secret key and warn if generated
        if not cls.validate_secret_key():
            app.logger.warning("Using generated SECRET_KEY. Set SECRET_KEY environment variable for production.")

        # Log development mode warning
        app.logger.warning("Running in development mode - not suitable for production!")
