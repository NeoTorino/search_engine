import time
import logging
from flask import Blueprint, render_template, request, jsonify

from services.search_service import search_jobs
from services.insights_service import get_combined_insights, get_organizations_insights
from lib.date_utils import get_date_range_days

# Import your security modules
from security.middleware.decorators import (
    secure_endpoint, get_sanitized_param,
    get_validation_result, is_request_safe
)
from security.monitoring import log_security_event

api = Blueprint('api', __name__)
security_logger = logging.getLogger('security')

# Define validation config for your search endpoints
SEARCH_VALIDATION_CONFIG = {
    'q': {'type': 'search', 'max_length': 200},
    'country': {'type': 'filter', 'max_length': 50},
    'countries': {'type': 'filter', 'max_length': 500},  # Multiple countries
    'organization': {'type': 'filter', 'max_length': 50},
    'organizations': {'type': 'filter', 'max_length': 500},  # Multiple orgs
    'source': {'type': 'filter', 'max_length': 50},
    'sources': {'type': 'filter', 'max_length': 200},  # Multiple sources
    'limit': {'type': 'general', 'max_length': 10},
    'offset': {'type': 'general', 'max_length': 10},
    'date_posted_days': {'type': 'general', 'max_length': 10}
}

def secure_get_search_params(max_countries=10, max_organizations=10, max_sources=5,
                           max_limit=100, max_offset=10000):
    """
    Secure version of get_search_params using the security framework
    """
    # Get sanitized parameters using the security framework
    query = get_sanitized_param('q', '').strip()

    # Handle countries (can be single or multiple)
    countries_raw = get_sanitized_param('countries', get_sanitized_param('country', []))
    if isinstance(countries_raw, str):
        countries = [c.strip() for c in countries_raw.split(',') if c.strip()]
    else:
        countries = countries_raw if isinstance(countries_raw, list) else []

    # Handle organizations
    orgs_raw = get_sanitized_param('organizations', get_sanitized_param('organization', []))
    if isinstance(orgs_raw, str):
        organizations = [o.strip() for o in orgs_raw.split(',') if o.strip()]
    else:
        organizations = orgs_raw if isinstance(orgs_raw, list) else []

    # Handle sources
    sources_raw = get_sanitized_param('sources', get_sanitized_param('source', []))
    if isinstance(sources_raw, str):
        sources = [s.strip() for s in sources_raw.split(',') if s.strip()]
    else:
        sources = sources_raw if isinstance(sources_raw, list) else []

    # Get numeric parameters with validation
    try:
        limit = min(int(get_sanitized_param('limit', 20)), max_limit)
    except (ValueError, TypeError):
        limit = 20

    try:
        offset = min(int(get_sanitized_param('offset', 0)), max_offset)
    except (ValueError, TypeError):
        offset = 0

    try:
        date_posted_days = int(get_sanitized_param('date_posted_days', 365)) if get_sanitized_param('date_posted_days') else None
        if date_posted_days and date_posted_days < 0:
            date_posted_days = 365
    except (ValueError, TypeError):
        date_posted_days = 365

    # Apply limits
    countries = countries[:max_countries]
    organizations = organizations[:max_organizations]
    sources = sources[:max_sources]

    return {
        'query': query,
        'countries': countries,
        'organizations': organizations,
        'sources': sources,
        'limit': limit,
        'offset': offset,
        'date_posted_days': date_posted_days
    }

@api.route("/insights")
@secure_endpoint(
    validation_config=SEARCH_VALIDATION_CONFIG,
    auto_sanitize=True,
    block_on_threat=True,
    log_threats=True
)
def api_insights():
    """Get all insights data in a single response: overview, jobs per day, top countries, and word cloud"""
    try:
        # Check if request passed security validation
        if not is_request_safe():
            security_logger.warning("Unsafe request blocked in combined_insights")
            return jsonify({"error": "Invalid request parameters"}), 400

        # Use secure parameter extraction
        search_params = secure_get_search_params()

        # Log security validation results for debugging
        query_validation = get_validation_result('q')
        if query_validation and query_validation.threats_detected:
            security_logger.info("Query threats detected but sanitized: %s", query_validation.threats_detected)

        # Get combined insights data
        data = get_combined_insights(search_params)

        # Validate response data before sending
        if not isinstance(data, dict):
            log_security_event("INVALID_RESPONSE_DATA", "Combined insights data is not a dictionary")
            return jsonify({"error": "Invalid response format"}), 500

        # Validate structure of combined response
        required_keys = ['overview', 'jobs_per_day', 'top_countries', 'word_cloud']
        if not all(key in data for key in required_keys):
            log_security_event("INCOMPLETE_INSIGHTS_DATA", f"Missing keys in response: {set(required_keys) - set(data.keys())}")
            return jsonify({"error": "Incomplete insights data"}), 500

        return jsonify(data)

    except ValueError as e:
        security_logger.warning("Invalid parameters in combined insights: %s", e)
        return jsonify({"error": "Invalid parameters"}), 400
    except Exception as e:
        security_logger.error("Error in combined insights: %s", e)
        log_security_event("INSIGHTS_ERROR", f"Combined insights error: {e}")
        return jsonify({"error": "Failed to load insights data"}), 500

@api.route("/organizations")
@secure_endpoint(
    validation_config=SEARCH_VALIDATION_CONFIG,
    auto_sanitize=True,
    block_on_threat=True,
    log_threats=True
)
def api_organizations():
    """Get organizations with job counts and last update dates"""
    try:
        # Check if request passed security validation
        if not is_request_safe():
            security_logger.warning("Unsafe request blocked in insights_organizations")
            return jsonify({"error": "Invalid request parameters"}), 400

        # Use secure parameter extraction
        search_params = secure_get_search_params()

        data = get_organizations_insights(search_params)

        # Validate response data
        if not isinstance(data, (dict, list)):
            log_security_event("INVALID_RESPONSE_DATA", "Organizations data is invalid")
            return jsonify({"error": "Invalid response format"}), 500

        return jsonify(data)

    except ValueError as e:
        security_logger.warning("Invalid parameters in organizations insights: %s", e)
        return jsonify({"error": "Invalid parameters"}), 400
    except Exception as e:
        security_logger.error("Error in organizations insights: %s", e)
        log_security_event("INSIGHTS_ERROR", f"Organizations insights error: {e}")
        return jsonify({"error": "Failed to load organizations data"}), 500

@api.route("/search")
@secure_endpoint(
    validation_config=SEARCH_VALIDATION_CONFIG,
    auto_sanitize=True,
    block_on_threat=True,
    log_threats=True
)
def api_search():
    """Main search endpoint with comprehensive security"""
    try:
        # Check if request passed security validation
        if not is_request_safe():
            security_logger.warning("Unsafe request blocked in search_results")
            return jsonify({"error": "Invalid request parameters"}), 400

        # Get standardized and validated search parameters using secure method
        params = secure_get_search_params(
            max_countries=10,
            max_organizations=10,
            max_sources=5,
            max_limit=100,
            max_offset=10000
        )

        # Extract parameters
        query = params['query']
        selected_countries = params['countries']
        selected_organizations = params['organizations']
        selected_sources = params['sources']
        days = params['date_posted_days'] or 365  # Default to 365 if None
        offset = params['offset']

        # Additional security: validate query length and content
        if len(query) > 200:
            security_logger.warning("Query too long: %d characters", len(query))
            return jsonify({"error": "Query too long"}), 400

        # Check if query is empty for template rendering
        is_empty_query = not bool(query.strip())

        # Convert days to date range (only if less than 31 days)
        date_range = None if days >= 31 else get_date_range_days(days)

        # Perform the search with sanitized parameters
        results, total_results, country_counts, organization_counts, source_counts, show_load_more = search_jobs(
            query, selected_countries, selected_organizations, selected_sources, date_range, offset
        )

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

    except Exception as e:
        security_logger.error("Error in search_results: %s", e)
        return jsonify({"error": "Search failed"}), 500
