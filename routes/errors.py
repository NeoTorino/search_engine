import time
import logging
import traceback
from flask import render_template, request
from utils.monitoring import log_security_event

security_logger = logging.getLogger('security')

def register_error_handlers(app, security_enforcer):
    """Register application-wide error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        log_security_event("BAD_REQUEST", str(error), severity="WARNING")
        return render_template('errors/400.html', time=time), 400

    @app.errorhandler(403)
    def forbidden(error):
        log_security_event("FORBIDDEN_ACCESS", str(error), severity="WARNING")
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
            log_security_event("SUSPICIOUS_404", f"Path: {path}", severity="WARNING")
            security_enforcer.increment_suspicious_activity(request.remote_addr)

        return render_template('errors/404.html', time=time), 404

    @app.errorhandler(413)
    def request_too_large(error):
        log_security_event("REQUEST_TOO_LARGE", f"Size: {request.content_length}", severity="ERROR")
        return render_template('errors/413.html', time=time), 413

    @app.errorhandler(422)
    def unprocessable_entity(error):
        log_security_event("UNPROCESSABLE_ENTITY", str(error), severity="WARNING")
        return render_template('errors/422.html', time=time), 422

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        log_security_event("RATE_LIMIT_EXCEEDED", f"IP: {request.remote_addr}", severity="ERROR")
        security_enforcer.increment_suspicious_activity(request.remote_addr)
        return render_template('errors/429.html', time=time), 429

    @app.errorhandler(500)
    def internal_error(error):
        security_logger.error("Internal server error: %s", error, exc_info=True)
        security_logger.error(traceback.format_exc())
        return render_template('errors/500.html', time=time), 500
