import os
import threading
import logging
from flask import Flask, redirect
from werkzeug.serving import make_server

from .ssl_context import create_ssl_context

class ProductionServer:
    """Production-hardened server configuration"""

    def __init__(self, app):
        self.app = app
        # Use your defined loggers
        self.general_logger = logging.getLogger('app.general')
        self.security_logger = logging.getLogger('app.security')
        self.error_logger = logging.getLogger('app.error')

        self._validate_production_requirements()

    def _validate_production_requirements(self):
        """Validate production environment requirements"""
        required_vars = [
            'SECRET_KEY',
            'REDIS_URL',
            'ALLOWED_HOSTS'
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            error_msg = f"Missing required production environment variables: {missing_vars}"
            self.error_logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate SSL certificates
        cert_path = os.getenv('CERT_PATH', './certs/entity/entity.crt')
        key_path = os.getenv('KEY_PATH', './certs/entity/entity.key')

        if not os.path.exists(cert_path):
            error_msg = f"SSL certificate file not found: {cert_path}"
            self.error_logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        if not os.path.exists(key_path):
            error_msg = f"SSL private key file not found: {key_path}"
            self.error_logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        self.security_logger.info("Production environment validation passed")

    def run(self):
        """Run production server configuration"""
        host = os.getenv('FLASK_HOST', '0.0.0.0')  # Bind to all interfaces in production
        ssl_port = int(os.getenv('SSL_PORT', '443'))
        http_port = int(os.getenv('HTTP_PORT', '80'))

        self.general_logger.info("Starting production HTTPS server on %s:%s", host, ssl_port)

        try:
            ssl_context = create_ssl_context()

            # Start HTTP redirect server if needed
            if os.getenv('FORCE_HTTPS', 'True').lower() == 'true':
                self.general_logger.info("Starting HTTP redirect server on %s:%s", host, http_port)
                self._start_http_redirect_server(host, http_port, ssl_port)

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
            self.error_logger.error("Failed to start production server: %s", e)
            raise ValueError(e)

    def _start_http_redirect_server(self, host, http_port, ssl_port):
        """Start HTTP redirect server in background"""
        def run_redirect_server():
            redirect_app = Flask('redirect')

            @redirect_app.route('/', defaults={'path': ''})
            @redirect_app.route('/<path:path>')
            def redirect_to_https(path):
                return redirect(f'https://{host}:{ssl_port}/{path}', code=301)

            try:
                redirect_server = make_server(host, http_port, redirect_app)
                self.general_logger.info("HTTP redirect server started successfully")
                redirect_server.serve_forever()
            except Exception as e:
                self.error_logger.error("HTTP redirect server failed: %s", e)

        redirect_thread = threading.Thread(target=run_redirect_server, daemon=True)
        redirect_thread.start()
