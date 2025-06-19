import time
import logging
from flask import Blueprint, render_template, request, jsonify

from services.search_service import search_jobs
from services.insights_service import get_combined_insights, get_organizations_insights
from services.filters_service import get_country_list, get_organization_list, get_source_list

from lib.date_utils import get_date_range_days

from utils.cache_store import cache

from security.core.sanitizers import sanitize_element
from security.monitoring import log_security_event

search = Blueprint('search', __name__)
security_logger = logging.getLogger('security')


CTY = cache.get_store_values('countries', get_country_list)
ORG = cache.get_store_values('organizations', get_organization_list)
SRC = cache.get_store_values('sources', get_source_list)


def get_parameters()-> dict:
    """
    Main function to sanitize all GET parameters with enhanced security
    Returns a dictionary with sanitized parameters
    """
    sanitized = {}

    # Sanitize 'q' parameter (free text for search)
    q = request.args.get('q', '')
    sanitized['q'] = sanitize_element(q, limit=256)

    # Sanitize 'country' parameter (list of predefined strings)
    countries = request.args.getlist('country')
    sanitized['country'] = sanitize_element(countries, valid_values=CTY, limit=10)

    # Sanitize 'organization' parameter (list of predefined strings)
    organizations = request.args.getlist('organization')
    sanitized['organization'] = sanitize_element(organizations, valid_values=ORG, limit=20)

    # Sanitize 'source' parameter (list of predefined strings)
    sources = request.args.getlist('source')
    sanitized['source'] = sanitize_element(sources, valid_values=SRC, limit=10)

    # Sanitize 'date_posted_days' parameter with enhanced security
    date_posted_days = request.args.get('date_posted_days', '365')
    sanitized['date_posted_days'] = sanitize_element(date_posted_days, default_value=365, min_value=0, max_value=365, limit=3)
    # Apply special rule: if > 30, set to 365
    if sanitized['date_posted_days'] == 30 and date_posted_days and str(date_posted_days).strip().isdigit():
        original_val = int(date_posted_days)
        if original_val > 30:
            sanitized['date_posted_days'] = 365

    # Sanitize 'from' parameter with enhanced security
    from_param = request.args.get('from', '0')
    sanitized['offset'] = sanitize_element(from_param, default_value=0, min_value=0, max_value=10000, limit=5)

    return sanitized

@search.route("/insights")
def search_insights():
    """Get all insights data in a single response: overview, jobs per day, top countries, and word cloud"""
    try:
        # Process ALL parameters with business logic in one call
        params = get_parameters()

        # Get combined insights data
        data = get_combined_insights(params)

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

@search.route("/organizations")
def search_organizations():
    """Get organizations with job counts and last update dates"""
    try:
        # Process ALL parameters with business logic in one call
        params = get_parameters()

        data = get_organizations_insights(params)

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

@search.route("/search")
def search_search():
    """Main search endpoint with comprehensive security"""
    try:
        # Process ALL parameters with business logic in one call
        params = get_parameters()

        # Extract processed parameters
        query = params['q']
        selected_countries = params['countries']  # Already processed as list, limited to 10
        selected_organizations = params['organizations']  # Already processed as list, limited to 10
        selected_sources = params['sources']  # Already processed as list, limited to 5
        offset = params['offset']  # Already validated range 0-10000
        days = params['date_posted_days']  # Already handles negatives -> 365

        # Check if query is empty for template rendering
        is_empty_query = not bool(query)

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
