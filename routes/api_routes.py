import logging
from flask import Blueprint, request, jsonify
from functools import wraps

from services.insights_service import (
    get_insights_overview, get_jobs_per_day,
    get_top_countries, get_word_cloud_data, get_organizations_insights
)
from utils.security import validate_search_query
from utils.monitoring import log_security_event

from security_config import SecurityConfig
from app_factory.extensions import get_extensions

api = Blueprint('api', __name__, url_prefix='/api')

security_logger = logging.getLogger('security')

def get_limiter():
    """Get limiter instance lazily"""
    extensions = get_extensions()
    return extensions.get('limiter')

def rate_limit(limit_string):
    """Decorator to apply rate limiting with lazy loading"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            limiter = get_limiter()
            if limiter:
                # Apply rate limiting
                limiter.limit(limit_string)(f)(*args, **kwargs)
                return f(*args, **kwargs)
            else:
                # If limiter not available, proceed without rate limiting
                return f(*args, **kwargs)
        return decorated_function
    return decorator

@api.route("/insights/overview")
@rate_limit(SecurityConfig.RATE_LIMITS['api'][2])
def insights_overview():
    """Get overview statistics: total jobs, organizations, average jobs per org"""
    try:
        data = get_insights_overview()
        return jsonify(data)
    except Exception as e:
        security_logger.error("Error in insights overview: %s", e)
        log_security_event("INSIGHTS_ERROR", f"Overview insights error: {e}")
        return jsonify({"error": "Failed to load overview insights"}), 500

@api.route("/insights/jobs-per-day")
@rate_limit(SecurityConfig.RATE_LIMITS['api'][2])
def insights_jobs_per_day():
    """Get jobs posted per day for the last 30 days"""
    try:
        data = get_jobs_per_day()
        return jsonify(data)
    except Exception as e:
        security_logger.error("Error in jobs per day: %s", e)
        log_security_event("INSIGHTS_ERROR", f"Jobs per day error: {e}")
        return jsonify({"error": "Failed to load jobs per day data"}), 500

@api.route("/insights/top-countries")
@rate_limit(SecurityConfig.RATE_LIMITS['api'][2])
def stats_top_countries():
    """Get top countries by job count"""
    try:
        data = get_top_countries()
        return jsonify(data)
    except Exception as e:
        security_logger.error("Error in top countries: %s", e)
        log_security_event("INSIGHTS_ERROR", f"Top countries error: {e}")
        return jsonify({"error": "Failed to load countries data"}), 500

@api.route("/insights/word-cloud")
@rate_limit(SecurityConfig.RATE_LIMITS['api'][2])
def insights_word_cloud():
    """Get word frequency data for job titles and descriptions"""
    search_term = request.args.get("q", "").strip()

    # Validate search term
    if search_term:
        is_valid, clean_search_term = validate_search_query(search_term)
        if not is_valid:
            log_security_event("INVALID_WORDCLOUD_QUERY", f"Query: {search_term}")
            return jsonify({"error": "Invalid search term"}), 400
        search_term = clean_search_term

    try:
        data = get_word_cloud_data(search_term=search_term)
        return jsonify(data)
    except Exception as e:
        security_logger.error("Error in word cloud: %s", e)
        log_security_event("INSIGHTS_ERROR", f"Word cloud error: {e}")
        return jsonify({"error": "Failed to load word cloud data"}), 500

@api.route("/insights/organizations")
@rate_limit(SecurityConfig.RATE_LIMITS['api'][2])
def insights_organizations():
    """Get organizations with job counts and last update dates"""
    try:
        data = get_organizations_insights()
        return jsonify(data)
    except Exception as e:
        security_logger.error("Error in organizations insights: %s", e)
        log_security_event("INSIGHTS_ERROR", f"Organizations insights error: {e}")
        return jsonify({"error": "Failed to load organizations data"}), 500