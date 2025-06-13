import logging
from flask import Blueprint, request, jsonify

from services.stats_service import (
    get_stats_overview, get_jobs_per_day,
    get_top_countries, get_word_cloud_data, get_organizations_stats
)
from utils.security import validate_search_query
from utils.monitoring import log_security_event

api = Blueprint('api', __name__, url_prefix='/api')

security_logger = logging.getLogger('security')

@api.route("/stats/overview")
def stats_overview():
    """Get overview statistics: total jobs, organizations, average jobs per org"""
    try:
        data = get_stats_overview()
        return jsonify(data)
    except Exception as e:
        security_logger.error("Error in stats overview: %s", e)
        log_security_event("STATS_ERROR", f"Overview stats error: {e}")
        return jsonify({"error": "Failed to load overview stats"}), 500

@api.route("/stats/jobs-per-day")
def stats_jobs_per_day():
    """Get jobs posted per day for the last 30 days"""
    try:
        data = get_jobs_per_day()
        return jsonify(data)
    except Exception as e:
        security_logger.error("Error in jobs per day: %s", e)
        log_security_event("STATS_ERROR", f"Jobs per day error: {e}")
        return jsonify({"error": "Failed to load jobs per day data"}), 500

@api.route("/stats/top-countries")
def stats_top_countries():
    """Get top countries by job count"""
    try:
        data = get_top_countries()
        return jsonify(data)
    except Exception as e:
        security_logger.error("Error in top countries: %s", e)
        log_security_event("STATS_ERROR", f"Top countries error: {e}")
        return jsonify({"error": "Failed to load countries data"}), 500

@api.route("/stats/word-cloud")
def stats_word_cloud():
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
        log_security_event("STATS_ERROR", f"Word cloud error: {e}")
        return jsonify({"error": "Failed to load word cloud data"}), 500

@api.route("/stats/organizations")
def stats_organizations():
    """Get organizations with job counts and last update dates"""
    try:
        data = get_organizations_stats()
        return jsonify(data)
    except Exception as e:
        security_logger.error("Error in organizations stats: %s", e)
        log_security_event("STATS_ERROR", f"Organizations stats error: {e}")
        return jsonify({"error": "Failed to load organizations data"}), 500
