import tempfile
from .base import BaseConfig

class TestingConfig(BaseConfig):
    """Testing configuration"""

    # Testing mode
    TESTING = True
    DEBUG = True

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

    # Use in-memory database for testing
    REDIS_URL = 'redis://localhost:6379/15'  # Use different DB for tests

    # Security settings (minimal for testing)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    PREFERRED_URL_SCHEME = 'http'

    # Disable rate limiting for tests
    RATELIMIT_ENABLED = False

    # Server settings
    FLASK_HOST = '127.0.0.1'
    HTTP_PORT = 5001  # Different port to avoid conflicts

    # Logging
    LOG_LEVEL = 'INFO'

    @classmethod
    def get_cert_paths(cls):
        """Get testing certificate paths (usually not needed)"""
        return {
            'cert_path': './certs/testing/test.crt',
            'key_path': './certs/testing/test.key'
        }

    @classmethod
    def init_app(cls, app):
        """Initialize testing-specific settings"""
        # Always use a generated secret key for tests
        import secrets
        cls.SECRET_KEY = secrets.token_hex(32)

        # Set up temporary directories if needed
        cls.TEMP_DIR = tempfile.mkdtemp()

        app.logger.info("Running in testing mode")