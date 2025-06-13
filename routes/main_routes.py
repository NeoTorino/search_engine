import time
from datetime import datetime
import logging
import traceback

from flask import Blueprint, render_template, request, jsonify, abort

from services.search_service import search_jobs, get_landing_stats
from services.stats_service import (
    get_stats_overview, get_jobs_per_day,
    get_top_countries, get_word_cloud_data, get_organizations_stats
)

from utils.utils import get_date_range_days
from utils.security import (
    sanitize_input, validate_search_query,
    validate_filter_values, validate_request_size
)
from utils.monitoring import log_security_event

main = Blueprint('main', __name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/security.log'),
        logging.StreamHandler()
    ]
)

security_logger = logging.getLogger('security')

@main.app_errorhandler(400)
def bad_request(error):
    log_security_event("BAD_REQUEST", str(error))
    return render_template('errors/400.html', time=time), 400

@main.app_errorhandler(404)
def page_not_found(error):
    log_security_event("PAGE_NOT_FOUND", str(error))
    return render_template('errors/404.html', time=time), 404

@main.app_errorhandler(413)
def request_entity_too_large(error):
    log_security_event("REQUEST_TOO_LARGE", str(error), severity="ERROR")
    return render_template('errors/413.html', time=time), 413

@main.app_errorhandler(429)
def rate_limit_exceeded(error):
    log_security_event("RATE_LIMIT_EXCEEDED", str(error), severity="ERROR")
    return render_template('errors/429.html', time=time), 429

@main.app_errorhandler(500)
def internal_server_error(error):
    # Log error but don't expose internal details
    security_logger.error("Internal error: %s", traceback.format_exc())
    return render_template('errors/500.html', time=time), 500

@main.route("/", methods=["GET"])
def index():
    total_jobs, total_orgs = get_landing_stats()
    return render_template('landing.html',
                            total_jobs=total_jobs,
                            total_orgs=total_orgs,
                            time=time)

# Health check endpoint (useful for load balancers)
@main.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}

@main.route("/search")
@validate_request_size(max_size=2048)  # Small limit for search
def search_results():
    # Enhanced input validation
    raw_query = request.args.get("q", "")

    # Validate query
    is_valid, clean_query = validate_search_query(raw_query)
    if not is_valid:
        log_security_event("INVALID_SEARCH_QUERY", f"Query: {raw_query}")
        abort(400)

    query = clean_query
    is_empty_query = not bool(query.strip())

    # Validate filters
    selected_countries = validate_filter_values(
        [sanitize_input(c) for c in request.args.getlist('country')],
        max_items=10
    )

    selected_organizations = validate_filter_values(
        [sanitize_input(o) for o in request.args.getlist('organization')],
        max_items=10
    )

    selected_sources = validate_filter_values(
        [sanitize_input(s) for s in request.args.getlist('source')],
        max_items=5
    )

    # Validate date range
    try:
        days = int(request.args.get('date_posted_days', 30))
        if days < 0 or days > 365:  # Reasonable limits
            days = 30
    except (ValueError, TypeError):
        days = 30

    # Validate offset
    try:
        offset = int(request.args.get('from', 0))
        if offset < 0 or offset > 10000:  # Prevent excessive pagination
            offset = 0
    except (ValueError, TypeError):
        offset = 0

    date_range = None if days >= 30 else get_date_range_days(days)

    print(f"query: '{query}' (empty: {is_empty_query})")
    print(f"date_range: {date_range}")
    print(f"selected_countries: {selected_countries}")
    print(f"selected_organizations: {selected_organizations}")
    print(f"selected_sources: {selected_sources}")

    results, total_results, country_counts, organization_counts, source_counts, show_load_more = search_jobs(
        query, selected_countries, selected_organizations, selected_sources, date_range, offset
    )
    print(f"total_results: {total_results}")
    print("-" * 40)

    # Handle AJAX requests (including empty query searches)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # For load more requests, only return the HTML results
        if offset > 0:
            rendered_results = render_template('_results.html', results=results)
            return rendered_results

        # For filter changes or empty query searches (offset = 0), return JSON with metadata
        rendered_results = render_template('_results.html', results=results)

        response_data = {
            'html': rendered_results,
            'total_results': total_results,
            'country_counts': country_counts or {},
            'organization_counts': organization_counts or {},
            'source_counts': source_counts or {},
            'show_load_more': show_load_more,
            'query': query,
            'is_empty_query': is_empty_query
        }
        return jsonify(response_data)

    # Always show search results page (even for empty queries)
    return render_template(
        'search.html',
        query=query,  # Always pass query variable (even if empty string)
        is_empty_query=is_empty_query,  # Always pass this flag
        offset=offset,
        results=results,
        total_results=total_results,
        show_load_more=show_load_more,
        country_counts=country_counts or {},
        organization_counts=organization_counts or {},
        source_counts=source_counts or {},
        selected_countries=selected_countries or [],
        selected_organizations=selected_organizations or [],
        selected_sources=selected_sources or [],
        date_posted_days=days,
        time=time
    )

@main.route("/about")
def about():
    return render_template("about.html", time=time)

@main.route("/organizations")
def organizations():
    return render_template("organizations.html", time=time)

@main.route("/sources")
def sources():
    return render_template("sources.html", time=time)

@main.route("/stats")
def stats():
    return render_template("stats.html", time=time)

# Stats API Routes
@main.route("/api/stats/overview")
def stats_overview():
    """Get overview statistics: total jobs, organizations, average jobs per org"""
    try:
        data = get_stats_overview()
        return jsonify(data)
    except Exception as e:
        print(f"Error in stats overview: {e}")
        log_security_event("STATS_ERROR", f"Overview stats error: {e}")
        return jsonify({"error": "Failed to load overview stats"}), 500

@main.route("/api/stats/jobs-per-day")
def stats_jobs_per_day():
    """Get jobs posted per day for the last 30 days"""
    try:
        data = get_jobs_per_day()
        return jsonify(data)
    except Exception as e:
        print(f"Error in jobs per day: {e}")
        log_security_event("STATS_ERROR", f"Jobs per day error: {e}")
        return jsonify({"error": "Failed to load jobs per day data"}), 500

@main.route("/api/stats/top-countries")
def stats_top_countries():
    """Get top countries by job count"""
    try:
        data = get_top_countries()
        return jsonify(data)
    except Exception as e:
        print(f"Error in top countries: {e}")
        log_security_event("STATS_ERROR", f"Top countries error: {e}")
        return jsonify({"error": "Failed to load countries data"}), 500

@main.route("/api/stats/word-cloud")
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
        print(f"Error in word cloud: {e}")
        log_security_event("STATS_ERROR", f"Word cloud error: {e}")
        return jsonify({"error": "Failed to load word cloud data"}), 500

@main.route("/api/stats/organizations")
def stats_organizations():
    """Get organizations with job counts and last update dates"""
    try:
        data = get_organizations_stats()
        return jsonify(data)
    except Exception as e:
        print(f"Error in organizations stats: {e}")
        log_security_event("STATS_ERROR", f"Organizations stats error: {e}")
        return jsonify({"error": "Failed to load organizations data"}), 500
