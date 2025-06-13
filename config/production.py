import os
from .base import BaseConfig

class ProductionConfig(BaseConfig):
    """Production configuration with enhanced security"""

    # Security settings
    DEBUG = False
    TESTING = False
    PROPAGATE_EXCEPTIONS = False

    # Enhanced session security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    PREFERRED_URL_SCHEME = 'https'

    # Production server settings
    FLASK_HOST = '0.0.0.0'  # Bind to all interfaces
    HTTP_PORT = int(os.getenv('HTTP_PORT', '80'))
    SSL_PORT = int(os.getenv('SSL_PORT', '443'))
    FORCE_HTTPS = True  # Always force HTTPS in production

    # Logging
    LOG_LEVEL = 'INFO'

    @classmethod
    def get_cert_paths(cls):
        """Get production certificate paths"""
        return {
            'cert_path': os.getenv('CERT_PATH', './certs/production/entity.crt'),
            'key_path': os.getenv('KEY_PATH', './certs/production/entity.key')
        }

    @classmethod
    def validate_production_requirements(cls):
        """Validate all production requirements"""
        required_vars = [
            'SECRET_KEY',
            'REDIS_URL',
            'ALLOWED_HOSTS'
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required production environment variables: {missing_vars}")

        # Validate SECRET_KEY
        if not cls.validate_secret_key():
            raise ValueError("Valid SECRET_KEY is required in production")

        # Validate SSL certificates exist
        cert_paths = cls.get_cert_paths()
        if not os.path.exists(cert_paths['cert_path']):
            raise FileNotFoundError(f"Certificate file not found: {cert_paths['cert_path']}")
        if not os.path.exists(cert_paths['key_path']):
            raise FileNotFoundError(f"Private key file not found: {cert_paths['key_path']}")

        return True

    @classmethod
    def init_app(cls, app):
        """Initialize production-specific settings"""
        # Validate all production requirements
        cls.validate_production_requirements()

        app.logger.info("Production environment validation passed")
