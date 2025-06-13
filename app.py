import os
import ssl
import secrets
import logging
import threading
from datetime import datetime, timedelta
import urllib3
import redis

from flask import Flask, request, redirect, g, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.serving import make_server

from dotenv import load_dotenv

from filters.custom_filters import register_filters
from middleware.secure_headers import apply_secure_headers
from utils.monitoring import security_monitor
from routes.main_routes import main

from security_config import (
    SecurityConfig, SecurityEnforcer, create_security_middleware,
    setup_enhanced_logging, log_security_event
)

# Load environment
load_dotenv(".env")

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup enhanced logging first
security_logger = setup_enhanced_logging()

class ProductionFlaskApp:
    """Production-hardened Flask application"""

    def __init__(self):
        self.app = Flask(__name__)
        self.setup_proxy_fix()
        self.setup_configuration()
        self.setup_security()
        self.setup_rate_limiting()
        self.setup_middleware()
        self.setup_routes()
        self.validate_production_requirements()

    def setup_proxy_fix(self):
        """Setup proxy handling for production deployment"""
        self.app.wsgi_app = ProxyFix(
            self.app.wsgi_app,
            x_for=1,
            x_proto=1,
            x_host=1,
            x_prefix=1
        )

    def setup_configuration(self):
        """Setup secure Flask configuration"""
        # Validate SECRET_KEY
        SECRET_KEY = os.environ.get('SECRET_KEY')
        if not SECRET_KEY or len(SECRET_KEY) < 32:
            if os.environ.get('FLASK_ENV') == 'production':
                raise ValueError("SECRET_KEY must be set and at least 32 characters long in production")
            else:
                security_logger.warning("Using generated SECRET_KEY. Set SECRET_KEY environment variable for production.")
                SECRET_KEY = secrets.token_hex(32)

        # Core security configuration
        self.app.config.update({
            'SECRET_KEY': SECRET_KEY,
            'PERMANENT_SESSION_LIFETIME': timedelta(hours=1),

            # Session security
            'SESSION_COOKIE_SECURE': True,
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Strict' if os.environ.get('FLASK_ENV') == 'production' else 'Lax',
            'SESSION_COOKIE_NAME': '__Secure-session',  # Secure prefix

            # CSRF protection
            'WTF_CSRF_TIME_LIMIT': 3600,
            'WTF_CSRF_SSL_STRICT': True,

            # Request limits
            'MAX_CONTENT_LENGTH': SecurityConfig.MAX_REQUEST_SIZE,
            'MAX_FORM_MEMORY_SIZE': SecurityConfig.MAX_REQUEST_SIZE,

            # File upload security (if needed in future)
            'UPLOAD_EXTENSIONS': SecurityConfig.ALLOWED_EXTENSIONS,

            # OpenObserve configuration
            'OPENOBSERVE_URL': os.getenv('OPENOBSERVE_URL'),
            'OPENOBSERVE_AUTH': os.getenv('OPENOBSERVE_AUTH'),

            # Cache settings
            'SEND_FILE_MAX_AGE_DEFAULT': 31536000,  # 1 year for static files

            # URL scheme
            'PREFERRED_URL_SCHEME': 'https' if os.getenv('FORCE_HTTPS', 'True').lower() == 'true' else 'http',
            'APPLICATION_ROOT': '/',

            # Production settings
            'DEBUG': False if os.environ.get('FLASK_ENV') == 'production' else os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
            'TESTING': False,
            'PROPAGATE_EXCEPTIONS': False if os.environ.get('FLASK_ENV') == 'production' else True,

            # Server configuration
            'SERVER_NAME': os.getenv('SERVER_NAME'),  # Set this in production
        })

    def setup_security(self):
        """Setup advanced security measures"""
        # Initialize Redis for security tracking
        try:
            redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
            redis_client.ping()  # Test connection
        except Exception as e:
            security_logger.error("Redis connection failed: %s", e)
            redis_client = None

        # Initialize security enforcer
        self.security_enforcer = SecurityEnforcer(redis_client)

        # Setup security middleware
        create_security_middleware(self.app, self.security_enforcer)

        # Setup security monitoring
        security_monitor.init_app(self.app)

    def setup_rate_limiting(self):
        """Setup advanced rate limiting"""
        redis_url = os.getenv('REDIS_URL', "redis://localhost:6379")

        self.limiter = Limiter(
            key_func=get_remote_address,
            app=self.app,
            storage_uri=redis_url,
            default_limits=SecurityConfig.RATE_LIMITS['default'],
            strategy="sliding-window-counter",
            headers_enabled=True,
            swallow_errors=True,  # Don't break app if Redis is down
        )

        # Apply different limits to different endpoints
        @self.limiter.limit(SecurityConfig.RATE_LIMITS['search'][2])  # Most restrictive
        def search_rate_limit():
            return request.endpoint == 'main.search_results'

        @self.limiter.limit(SecurityConfig.RATE_LIMITS['api'][2])
        def api_rate_limit():
            return request.endpoint and request.endpoint.startswith('main.api.')

    def setup_middleware(self):
        """Setup all middleware"""
        # Error handlers
        self.setup_error_handlers()

        # Security headers
        self.app.after_request(apply_secure_headers)

        # Request hooks
        @self.app.before_request
        def before_request_security():
            # Force HTTPS redirect
            if os.getenv('FORCE_HTTPS', 'True').lower() == 'true':
                if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
                    if request.endpoint not in ['main.health_check']:
                        return redirect(request.url.replace('http://', 'https://'), code=301)

            # Set CSP nonce
            g.csp_nonce = secrets.token_urlsafe(16)

            # Log request for monitoring
            if request.endpoint in SecurityConfig.SENSITIVE_ENDPOINTS:
                log_security_event("SENSITIVE_ENDPOINT_ACCESS", f"Endpoint: {request.endpoint}")

        @self.app.context_processor
        def inject_security_context():
            """Inject security context into templates"""
            return {
                'nonce': getattr(g, 'csp_nonce', ''),
                'year': datetime.utcnow().year,
                'is_secure': request.is_secure,
                'scheme': request.scheme
            }

    def setup_error_handlers(self):
        """Setup comprehensive error handling"""

        @self.app.errorhandler(400)
        def bad_request(error):
            log_security_event("BAD_REQUEST", str(error), severity="WARNING")
            return {"error": "Bad Request", "code": 400}, 400

        @self.app.errorhandler(403)
        def forbidden(error):
            log_security_event("FORBIDDEN_ACCESS", str(error), severity="WARNING")
            return {"error": "Access Forbidden", "code": 403}, 403

        @self.app.errorhandler(404)
        def not_found(error):
            path = request.path
            # Log suspicious 404s
            suspicious_patterns = [
                '.php', '.asp', '.jsp', 'wp-admin', 'admin', '.env', 'config',
                'phpmyadmin', 'xmlrpc', 'wp-login', '.git', 'backup'
            ]

            if any(pattern in path.lower() for pattern in suspicious_patterns):
                log_security_event("SUSPICIOUS_404", f"Path: {path}", severity="WARNING")
                # Increment suspicious activity counter
                self.security_enforcer.increment_suspicious_activity(request.remote_addr)

            return {"error": "Not Found", "code": 404}, 404

        @self.app.errorhandler(413)
        def request_too_large(error):
            log_security_event("REQUEST_TOO_LARGE", f"Size: {request.content_length}", severity="ERROR")
            return {"error": "Request Too Large", "code": 413}, 413

        @self.app.errorhandler(422)
        def unprocessable_entity(error):
            log_security_event("UNPROCESSABLE_ENTITY", str(error), severity="WARNING")
            return {"error": "Unprocessable Entity", "code": 422}, 422

        @self.app.errorhandler(429)
        def rate_limit_exceeded(error):
            log_security_event("RATE_LIMIT_EXCEEDED", f"IP: {request.remote_addr}", severity="ERROR")
            # Block IP after multiple rate limit violations
            self.security_enforcer.increment_suspicious_activity(request.remote_addr)
            return {"error": "Rate Limit Exceeded", "code": 429}, 429

        @self.app.errorhandler(500)
        def internal_error(error):
            security_logger.error(f"Internal server error: {error}", exc_info=True)
            return {"error": "Internal Server Error", "code": 500}, 500

    def setup_routes(self):
        """Setup application routes"""
        register_filters(self.app)
        self.app.register_blueprint(main)

    def validate_production_requirements(self):
        """Validate production environment requirements"""
        if os.environ.get('FLASK_ENV') == 'production':
            required_vars = [
                'SECRET_KEY',
                'REDIS_URL',
                'ALLOWED_HOSTS'
            ]

            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise ValueError(f"Missing required production environment variables: {missing_vars}")

            # Validate SSL certificates
            cert_path = os.getenv('CERT_PATH', './certs/entity/entity.crt')
            key_path = os.getenv('KEY_PATH', './certs/entity/entity.key')

            if not os.path.exists(cert_path) or not os.path.exists(key_path):
                raise FileNotFoundError("SSL certificates required for production")

            security_logger.info("Production environment validation passed")

    def create_ssl_context(self):
        """Create enhanced SSL context"""
        cert_path = os.getenv('CERT_PATH', './certs/entity/entity.crt')
        key_path = os.getenv('KEY_PATH', './certs/entity/entity.key')

        if not os.path.exists(cert_path):
            raise FileNotFoundError(f"Certificate file not found: {cert_path}")
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"Private key file not found: {key_path}")

        # Create SSL context with maximum security
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_path, key_path)

        # Enhanced security settings
        context.set_ciphers(
            'ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS:!3DES:!RC4'
        )

        # Use only TLS 1.2 and 1.3
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_3

        # Security options
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        context.options |= ssl.OP_SINGLE_DH_USE
        context.options |= ssl.OP_SINGLE_ECDH_USE
        context.options |= ssl.OP_NO_COMPRESSION

        # Set ECDH curve
        context.set_ecdh_curve('prime256v1')

        return context

    def run_production_server(self):
        """Run production server configuration"""
        host = os.getenv('FLASK_HOST', '0.0.0.0')  # Bind to all interfaces in production
        ssl_port = int(os.getenv('SSL_PORT', '443'))
        http_port = int(os.getenv('HTTP_PORT', '80'))

        security_logger.info(f"Starting production server on {host}:{ssl_port}")

        try:
            ssl_context = self.create_ssl_context()

            # Start HTTP redirect server if needed
            if os.getenv('FORCE_HTTPS', 'True').lower() == 'true':
                self.start_http_redirect_server(host, http_port, ssl_port)

            # Run HTTPS server
            self.app.run(
                host=host,
                port=ssl_port,
                ssl_context=ssl_context,
                threaded=True,
                use_reloader=False,  # Never use reloader in production
                debug=False
            )

        except Exception as e:
            security_logger.error(f"Failed to start production server: {e}")
            raise

    def start_http_redirect_server(self, host, http_port, ssl_port):
        """Start HTTP redirect server in background"""
        def run_redirect_server():
            redirect_app = Flask('redirect')

            @redirect_app.route('/', defaults={'path': ''})
            @redirect_app.route('/<path:path>')
            def redirect_to_https(path):
                return redirect(f'https://{host}:{ssl_port}/{path}', code=301)

            try:
                redirect_server = make_server(host, http_port, redirect_app)
                security_logger.info(f"HTTP redirect server running on {host}:{http_port}")
                redirect_server.serve_forever()
            except Exception as e:
                security_logger.error(f"HTTP redirect server failed: {e}")

        redirect_thread = threading.Thread(target=run_redirect_server, daemon=True)
        redirect_thread.start()

    def run_development_server(self):
        """Run development server with security warnings"""
        host = os.getenv('FLASK_HOST', '127.0.0.1')
        port = int(os.getenv('HTTP_PORT', '5000'))
        debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

        security_logger.warning("Running in development mode - not suitable for production!")

        self.app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )

# Initialize application
def create_app():
    """Application factory"""
    return ProductionFlaskApp()

# Main execution
if __name__ == '__main__':
    app_instance = create_app()

    if os.getenv('FLASK_ENV') == 'production':
        app_instance.run_production_server()
    else:
        app_instance.run_development_server()

# Export app for WSGI servers
app = create_app().app