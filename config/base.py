import os
import secrets
from datetime import timedelta
from security_config import SecurityConfig

class BaseConfig:
    """Base configuration class with common settings"""

    # Core Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY')
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)

    # Request limits
    MAX_CONTENT_LENGTH = SecurityConfig.MAX_REQUEST_SIZE
    MAX_FORM_MEMORY_SIZE = SecurityConfig.MAX_REQUEST_SIZE

    # File upload security
    UPLOAD_EXTENSIONS = SecurityConfig.ALLOWED_EXTENSIONS

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'  # Override in production
    SESSION_COOKIE_NAME = '__Secure-session' if os.getenv('FLASK_ENV') == 'production' else 'session'

    # CSRF protection
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = True

    # Cache settings
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year for static files

    # Application settings
    APPLICATION_ROOT = '/'
    PROPAGATE_EXCEPTIONS = True  # Override in production

    # External services
    OPENOBSERVE_URL = os.getenv('OPENOBSERVE_URL')
    OPENOBSERVE_AUTH = os.getenv('OPENOBSERVE_AUTH')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

    # Server configuration
    FLASK_HOST = os.getenv('FLASK_HOST', '127.0.0.1')
    HTTP_PORT = int(os.getenv('HTTP_PORT', '5000'))
    SSL_PORT = int(os.getenv('SSL_PORT', '5443'))
    SERVER_NAME = os.getenv('SERVER_NAME')

    # Security settings
    FORCE_HTTPS = os.getenv('FORCE_HTTPS', 'False').lower() == 'true'
    DEV_HTTPS = os.getenv('DEV_HTTPS', 'False').lower() == 'true'
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',') if os.getenv('ALLOWED_HOSTS') else []

    # Rate limiting
    RATE_LIMITS = SecurityConfig.RATE_LIMITS
    SENSITIVE_ENDPOINTS = SecurityConfig.SENSITIVE_ENDPOINTS

    @classmethod
    def validate_secret_key(cls):
        """Validate SECRET_KEY requirements"""
        if not cls.SECRET_KEY or len(cls.SECRET_KEY) < 32:
            if os.environ.get('FLASK_ENV') == 'production':
                raise ValueError("SECRET_KEY must be set and at least 32 characters long in production")
            else:
                # Generate a temporary key for development
                cls.SECRET_KEY = secrets.token_hex(32)
                return False  # Indicates using generated key
        return True  # Indicates using provided key

    @classmethod
    def get_cert_paths(cls):
        """Get certificate paths - to be overridden by subclasses"""
        return {
            'cert_path': './certs/development/dev.crt',
            'key_path': './certs/development/dev.key'
        }
