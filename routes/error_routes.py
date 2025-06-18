import time
import logging
import traceback

from flask import Blueprint, render_template

from security.monitoring import log_security_event

error = Blueprint('error', __name__)

security_logger = logging.getLogger('security')

@error.app_errorhandler(400)
def bad_request(err):
    log_security_event("BAD_REQUEST", str(err))
    return render_template('errors/400.html', time=time), 400

@error.app_errorhandler(404)
def page_not_found(err):
    log_security_event("PAGE_NOT_FOUND", str(err))
    return render_template('errors/404.html', time=time), 404

@error.app_errorhandler(413)
def request_entity_too_large(err):
    log_security_event("REQUEST_TOO_LARGE", str(err), severity="ERROR")
    return render_template('errors/413.html', time=time), 413

@error.app_errorhandler(429)
def rate_limit_exceeded(err):
    log_security_event("RATE_LIMIT_EXCEEDED", str(err), severity="ERROR")
    return render_template('errors/429.html', time=time), 429

@error.app_errorhandler(500)
def internal_server_error():
    # Log error but don't expose internal details
    security_logger.error("Internal error: %s", traceback.format_exc())
    return render_template('errors/500.html', time=time), 500