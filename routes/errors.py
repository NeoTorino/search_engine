import time
from flask import render_template, request

def register_error_handlers(app, security_enforcer):
    """Register application-wide error handlers"""

    @app.errorhandler(400)
    def bad_request(error):
        return render_template('errors/400.html', time=time), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', time=time), 403

    @app.errorhandler(404)
    def not_found(error):
        path = request.path
        # Log suspicious 404s
        suspicious_patterns = [
            '.php', '.asp', '.jsp', 'wp-admin', 'admin', '.env', 'config',
            'phpmyadmin', 'xmlrpc', 'wp-login', '.git', 'backup'
        ]

        if any(pattern in path.lower() for pattern in suspicious_patterns):
            security_enforcer.increment_suspicious_activity(request.remote_addr)

        return render_template('errors/404.html', time=time), 404

    @app.errorhandler(413)
    def request_too_large(error):
        return render_template('errors/413.html', time=time), 413

    @app.errorhandler(422)
    def unprocessable_entity(error):
        return render_template('errors/422.html', time=time), 422

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        security_enforcer.increment_suspicious_activity(request.remote_addr)
        return render_template('errors/429.html', time=time), 429

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html', time=time), 500
