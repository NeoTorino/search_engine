import os
import threading
import socket
from flask import Flask, redirect
from werkzeug.serving import make_server
from security.monitoring import security_monitor
from .ssl_context import create_ssl_context

class DevelopmentServer:
    """Development server with optional HTTPS support"""

    def __init__(self, app):
        self.app = app
        self.security_logger = security_monitor.logger

    def run(self):
        """Run development server with optional HTTPS support"""
        host = os.getenv('FLASK_HOST', '127.0.0.1')
        http_port = int(os.getenv('HTTP_PORT', '5000'))
        ssl_port = int(os.getenv('SSL_PORT', '5443'))
        debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

        # Check if HTTPS should be enabled in development
        use_dev_https = os.getenv('DEV_HTTPS', 'False').lower() == 'true'
        force_https = os.getenv('FORCE_HTTPS', 'False').lower() == 'true'

        self.security_logger.warning("Running in development mode - not suitable for production!")

        if use_dev_https:
            self._run_https_server(host, ssl_port, http_port, debug, force_https)
        else:
            self._run_http_server(host, http_port, debug)

    def _is_port_available(self, host, port):
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                return True
        except OSError:
            return False

    def _run_https_server(self, host, ssl_port, http_port, debug, force_https):
        """Run HTTPS development server"""
        try:
            ssl_context = create_ssl_context()
            self.security_logger.info("Starting development HTTPS server on %s:%s", host, ssl_port)

            # Start HTTP redirect server if FORCE_HTTPS is enabled
            if force_https:
                if self._is_port_available(host, http_port):
                    self._start_http_redirect_server(host, http_port, ssl_port)
                else:
                    self.security_logger.warning(
                        "HTTP port %s is already in use. HTTP redirect server will not start. "
                        "Set HTTP_PORT to a different port or disable FORCE_HTTPS in development.",
                        http_port
                    )

            self.app.run(
                host=host,
                port=ssl_port,
                ssl_context=ssl_context,
                debug=debug,
                threaded=True
            )
        except FileNotFoundError as e:
            self.security_logger.error("SSL certificates not found: %s", e)
            self.security_logger.info("Please generate certificates or set DEV_HTTPS=False")
            self.security_logger.info(
                "To generate certificates: mkdir -p certs/development && "
                "openssl req -x509 -newkey rsa:2048 -keyout certs/development/dev.key "
                "-out certs/development/dev.crt -days 365 -nodes -subj '/CN=localhost'"
            )
            raise
        except Exception as e:
            self.security_logger.error("Failed to start HTTPS server: %s", e)
            raise

    def _run_http_server(self, host, http_port, debug):
        """Run HTTP development server"""
        if not self._is_port_available(host, http_port):
            self.security_logger.error("Port %s is already in use. Please use a different port.", http_port)
            # Try to find an available port
            for port in range(http_port + 1, http_port + 100):
                if self._is_port_available(host, port):
                    self.security_logger.info("Using available port %s instead", port)
                    http_port = port
                    break
            else:
                raise OSError(f"No available ports found near {http_port}")

        self.security_logger.info("Starting development HTTP server on %s:%s", host, http_port)
        self.app.run(
            host=host,
            port=http_port,
            debug=debug,
            threaded=True
        )

    def _start_http_redirect_server(self, host, http_port, ssl_port):
        """Start HTTP redirect server in background for development"""
        def run_redirect_server():
            redirect_app = Flask('redirect')

            @redirect_app.route('/', defaults={'path': ''})
            @redirect_app.route('/<path:path>')
            def redirect_to_https(path):
                return redirect(f'https://{host}:{ssl_port}/{path}', code=301)

            try:
                redirect_server = make_server(host, http_port, redirect_app)
                self.security_logger.info("HTTP redirect server running on %s:%s", host, http_port)
                redirect_server.serve_forever()
            except Exception as e:
                self.security_logger.error("HTTP redirect server failed: %s", e)

        redirect_thread = threading.Thread(target=run_redirect_server, daemon=True)
        redirect_thread.start()