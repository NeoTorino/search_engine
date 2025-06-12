import os
from datetime import datetime, timedelta
import secrets
import urllib3
from flask import Flask, request, redirect, url_for, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis

from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

from filters.custom_filters import register_filters
from middleware.secure_headers import apply_secure_headers
from routes.main_routes import main

# Load environment
load_dotenv(".env")

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

# HTTPS Configuration
CERT_PATH = os.getenv('CERT_PATH', './certs/entity/entity.crt')
KEY_PATH = os.getenv('KEY_PATH', './certs/entity/entity.key')
FORCE_HTTPS = os.getenv('FORCE_HTTPS', 'True').lower() == 'true'
SSL_PORT = int(os.getenv('SSL_PORT', '5443'))
HTTP_PORT = int(os.getenv('HTTP_PORT', '5000'))

limiter = Limiter(
    app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",  # Configure your Redis
    default_limits=["1000 per day", "100 per hour"]
)

@app.before_request
def force_https():
    """Redirect HTTP to HTTPS if FORCE_HTTPS is enabled"""
    if FORCE_HTTPS and not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
        # Skip redirect for health checks or specific paths if needed
        if request.endpoint not in ['health_check']:  # Add your exempt endpoints here
            return redirect(request.url.replace('http://', 'https://').replace(f':{HTTP_PORT}', f':{SSL_PORT}'))

@app.before_request
def set_nonce():
    g.csp_nonce = secrets.token_urlsafe(16)

@app.context_processor
def inject_nonce():
    return dict(nonce=g.csp_nonce)

@app.context_processor
def inject_now():
    return {'year': datetime.utcnow().year}

@app.context_processor
def inject_security_context():
    """Inject security-related context variables"""
    return {
        'is_secure': request.is_secure,
        'scheme': request.scheme
    }

# Register secure headers
app.after_request(apply_secure_headers)

# Register Jinja2 filters
register_filters(app)

# Register blueprints
app.register_blueprint(main)

# Security configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(32)),
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    WTF_CSRF_TIME_LIMIT=3600,
    MAX_CONTENT_LENGTH=1024*1024,  # 1MB max request size
)

# Disable debug in production
if os.environ.get('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
    app.config['TESTING'] = False

def create_ssl_context():
    """Create SSL context for HTTPS"""
    import ssl
    
    # Check if certificate files exist
    if not os.path.exists(CERT_PATH):
        raise FileNotFoundError(f"Certificate file not found: {CERT_PATH}")
    if not os.path.exists(KEY_PATH):
        raise FileNotFoundError(f"Private key file not found: {KEY_PATH}")
    
    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT_PATH, KEY_PATH)
    
    # Security settings
    context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    return context

if __name__ == '__main__':
    # Development server configuration
    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    
    print(f"Certificate path: {CERT_PATH}")
    print(f"Private key path: {KEY_PATH}")
    print(f"Force HTTPS: {FORCE_HTTPS}")
    
    try:
        if os.path.exists(CERT_PATH) and os.path.exists(KEY_PATH):
            print(f"Starting HTTPS server on https://{host}:{SSL_PORT}")
            ssl_context = create_ssl_context()
            
            if FORCE_HTTPS:
                # Start HTTP server for redirects in a separate thread
                import threading
                from werkzeug.serving import make_server
                
                def run_http_redirect():
                    redirect_app = Flask('redirect')
                    
                    @redirect_app.route('/', defaults={'path': ''})
                    @redirect_app.route('/<path:path>')
                    def redirect_to_https(path):
                        return redirect(f'https://{host}:{SSL_PORT}/{path}', code=301)
                    
                    http_server = make_server(host, HTTP_PORT, redirect_app)
                    print(f"HTTP redirect server running on http://{host}:{HTTP_PORT}")
                    http_server.serve_forever()
                
                # Start HTTP redirect server in background
                http_thread = threading.Thread(target=run_http_redirect, daemon=True)
                http_thread.start()
            
            # Start HTTPS server
            app.run(
                host=host,
                port=SSL_PORT,
                debug=debug_mode,
                ssl_context=ssl_context
            )
        else:
            print("SSL certificates not found. Starting HTTP server...")
            print("Run the certificate generation script first: ./generate-certs.sh")
            app.run(
                host=host,
                port=HTTP_PORT,
                debug=debug_mode
            )
            
    except Exception as e:
        print(f"Error starting server: {e}")
        print("Falling back to HTTP server...")
        app.run(
            host=host,
            port=HTTP_PORT,
            debug=debug_mode
        )