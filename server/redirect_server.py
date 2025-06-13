import threading
from flask import Flask, redirect
from werkzeug.serving import make_server

class HTTPRedirectServer:
    """HTTP to HTTPS redirect server"""

    def __init__(self, host='0.0.0.0', http_port=80, https_port=443, logger=None):
        self.host = host
        self.http_port = http_port
        self.https_port = https_port
        self.logger = logger
        self.server = None
        self.thread = None

    def create_redirect_app(self):
        """Create Flask app that redirects all HTTP to HTTPS"""
        redirect_app = Flask('redirect')

        @redirect_app.route('/', defaults={'path': ''})
        @redirect_app.route('/<path:path>')
        def redirect_to_https(path):
            # Construct HTTPS URL
            https_url = f'https://{self.host}'

            # Add port if not standard HTTPS port
            if self.https_port != 443:
                https_url += f':{self.https_port}'

            # Add path
            if path:
                https_url += f'/{path}'

            return redirect(https_url, code=301)

        @redirect_app.errorhandler(404)
        def redirect_404(error):
            return redirect(f'https://{self.host}:{self.https_port}/', code=301)

        return redirect_app

    def start(self):
        """Start the HTTP redirect server in a background thread"""
        if self.thread and self.thread.is_alive():
            if self.logger:
                self.logger.warning("HTTP redirect server already running")
            return

        def run_redirect_server():
            try:
                redirect_app = self.create_redirect_app()
                self.server = make_server(self.host, self.http_port, redirect_app)

                if self.logger:
                    self.logger.info("HTTP redirect server running on %s:%s", self.host, self.http_port)

                self.server.serve_forever()

            except Exception as e:
                if self.logger:
                    self.logger.error("HTTP redirect server failed: %s", e)
                raise

        self.thread = threading.Thread(target=run_redirect_server, daemon=True)
        self.thread.start()

        if self.logger:
            self.logger.info("HTTP redirect server started")

    def stop(self):
        """Stop the HTTP redirect server"""
        if self.server:
            self.server.shutdown()
            if self.logger:
                self.logger.info("HTTP redirect server stopped")

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

def start_http_redirect_server(host, http_port, https_port, logger=None):
    """Convenience function to start HTTP redirect server"""
    redirect_server = HTTPRedirectServer(host, http_port, https_port, logger)
    redirect_server.start()
    return redirect_server
