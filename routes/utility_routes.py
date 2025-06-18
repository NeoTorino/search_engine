from datetime import datetime
from flask import Blueprint, make_response

from security.middleware.decorators import secure_endpoint

utility = Blueprint('utility', __name__)

@utility.route("/robots.txt", methods=["GET"])
@secure_endpoint(
    validation_config={},  # No special validation needed
    auto_sanitize=False,
    block_on_threat=False,
    log_threats=False
)
def robots_txt():
    """
    Serve robots.txt file for web crawlers from template folder
    """
    try:
        with open('templates/robots.txt', 'r', encoding='utf-8') as f:
            robots_content = f.read()
    except FileNotFoundError:
        # Fallback if file doesn't exist
        robots_content = "User-agent: *\nAllow: /"

    response = make_response(robots_content)
    response.headers['Content-Type'] = 'text/plain'
    return response

@utility.route('/health')
@secure_endpoint(
    validation_config={},  # No special validation needed
    auto_sanitize=False,
    block_on_threat=False,
    log_threats=False
)
def health_check():
    """Health check endpoint (useful for load balancers)"""
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
