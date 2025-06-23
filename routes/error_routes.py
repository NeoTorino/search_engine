import time
import logging
import traceback

from flask import Blueprint, render_template, request, jsonify

error_bp = Blueprint('error', __name__, url_prefix='/error')

logger = logging.getLogger('app.error')


def render_error_page(error_code, template_name=None):
    """Helper function to render error pages consistently"""
    if template_name is None:
        template_name = f'errors/{error_code}.html'

    return render_template(template_name, time=time), error_code


def is_ajax_request():
    """Check if the request is an AJAX request"""
    return (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            request.headers.get('Content-Type') == 'application/json' or
            'application/json' in request.headers.get('Accept', ''))


def register_error_handlers(app, security_enforcer):
    """Register application-wide error handlers"""

    @app.errorhandler(400)
    def bad_request(error):
        logger.error("[400] Bad Request")
        logger.error(error)

        if is_ajax_request():
            return jsonify({
                'error': 'Bad Request',
                'message': 'The request could not be understood by the server.',
                'status': 400
            }), 400

        return render_error_page(400)

    @app.errorhandler(403)
    def forbidden(error):
        logger.error("[403] Forbidden Error")
        logger.error(error)

        if is_ajax_request():
            return jsonify({
                'error': 'Forbidden',
                'message': 'Access to this resource is forbidden.',
                'status': 403
            }), 403

        return render_error_page(403)

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

        logger.error("[404] Page Not Found")
        logger.error(error)

        if is_ajax_request():
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found.',
                'status': 404
            }), 404

        return render_error_page(404)

    @app.errorhandler(413)
    def request_too_large(error):
        logger.error("Request Too Large")
        logger.error(error)

        if is_ajax_request():
            return jsonify({
                'error': 'Request Too Large',
                'message': 'The request is too large to process.',
                'status': 413
            }), 413

        return render_error_page(413)

    @app.errorhandler(422)
    def unprocessable_entity(error):
        logger.error("[422] Unprocessable Entity")
        logger.error(error)

        if is_ajax_request():
            return jsonify({
                'error': 'Unprocessable Entity',
                'message': 'The request was well-formed but contains semantic errors.',
                'status': 422
            }), 422

        return render_error_page(422)

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        logger.error("[429] Rate Limit Exceeded")
        logger.error(error)
        security_enforcer.increment_suspicious_activity(request.remote_addr)

        if is_ajax_request():
            return jsonify({
                'error': 'Too Many Requests',
                'message': 'You have made too many requests in a short period of time. Please wait before trying again.',
                'status': 429,
                'retry_after': 60
            }), 429

        return render_error_page(429)

    @app.errorhandler(500)
    def internal_error(error):
        logger.error("[500] Internal Error")
        logger.error(error)
        logger.error(traceback.format_exc())

        if is_ajax_request():
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred. Please try again later.',
                'status': 500
            }), 500

        return render_error_page(500)


# Dedicated error page routes using the helper function
@error_bp.route('/400')
def error_400():
    """Dedicated 400 error page"""
    return render_error_page(400)

@error_bp.route('/403')
def error_403():
    """Dedicated 403 error page"""
    return render_error_page(403)

@error_bp.route('/404')
def error_404():
    """Dedicated 404 error page"""
    return render_error_page(404)

@error_bp.route('/413')
def error_413():
    """Dedicated 413 error page"""
    return render_error_page(413)

@error_bp.route('/422')
def error_422():
    """Dedicated 422 error page"""
    return render_error_page(422)

@error_bp.route('/429')
def error_429():
    """Dedicated 429 error page"""
    return render_error_page(429)

@error_bp.route('/500')
def error_500():
    """Dedicated 500 error page"""
    return render_error_page(500)
