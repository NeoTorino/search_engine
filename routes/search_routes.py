import time
import logging
from flask import Blueprint, render_template, request, jsonify, g

from services.search_service import search_jobs
from services.insights_service import get_combined_insights, get_organizations_insights
from services.filters_service import get_country_list, get_organization_list, get_source_list

from utils.date_utils import get_date_range_days
from utils.cache_store import cache
from utils.sanitizers import sanitize_element

from decorators.sanitizer import sanitize_params
from decorators.debug import debug

search_bp = Blueprint('search', __name__)
security_logger = logging.getLogger('security')


CTY = cache.get_store_values('countries', get_country_list)
ORG = cache.get_store_values('organizations', get_organization_list)
SRC = cache.get_store_values('sources', get_source_list)


# Configuration to replace your existing sanitization function
sanitization_config = {
    'q': {
        'source': 'args',
        'method': 'get',
        'default': '',
        'sanitizer': lambda x: sanitize_element(x, limit=(0, 500)),
        'result_key': 'q'
    },

    'country': {
        'source': 'args',
        'method': 'getlist',
        'default': [],
        'sanitizer': lambda x: sanitize_element(x, valid_values=CTY, limit=(20, 200)),
        'result_key': 'countries'
    },

    'organization': {
        'source': 'args',
        'method': 'getlist',
        'default': [],
        'sanitizer': lambda x: sanitize_element(x, valid_values=ORG, limit=(30, 500)),
        'result_key': 'organizations'
    },

    'source': {
        'source': 'args',
        'method': 'getlist',
        'default': [],
        'sanitizer': lambda x: sanitize_element(x, valid_values=SRC, limit=(10, 200)),
        'result_key': 'sources'
    },

    'date_posted_days': {
        'source': 'args',
        'method': 'get',
        'default': '365',
        'sanitizer': lambda x: sanitize_element(x, default_value=365, min_value=0, max_value=31, limit=(0, 2)),
        'result_key': 'date_posted_days',
        'custom_logic': lambda x: 365 if (x and x > 30) or (x and x < 0) else x
    },

    'from': {
        'source': 'args',
        'method': 'get',
        'default': '0',
        'sanitizer': lambda x: sanitize_element(x, default_value=0, min_value=0, max_value=10000, limit=(0, 5)),
        'result_key': 'offset'
    }
}


@search_bp.route("/insights")
@sanitize_params(sanitization_config)
@debug()
def insights():
    """Get all insights data in a single response: overview, jobs per day, top countries, and word cloud"""
    try:
        # Access sanitized parameters directly from g
        params = g.sanitized_params

        # Get combined insights data
        data = get_combined_insights(params)

        print(data)
        # Validate response data before sending
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid response format"}), 500

        # Validate structure of combined response
        required_keys = ['overview', 'jobs_per_day', 'top_countries', 'word_cloud']
        if not all(key in data for key in required_keys):
            return jsonify({"error": "Incomplete insights data"}), 500

        return jsonify(data)

    except ValueError as e:
        security_logger.warning("Invalid parameters in combined insights: %s", e)
        return jsonify({"error": "Invalid parameters"}), 400
    except Exception as e:
        security_logger.error("Error in combined insights: %s", e)
        return jsonify({"error": "Failed to load insights data"}), 500


@search_bp.route("/organizations")
@sanitize_params(sanitization_config)
@debug()
def organizations():
    """Get organizations with job counts and last update dates"""
    try:
        # Access sanitized parameters directly from g
        params = g.sanitized_params

        data = get_organizations_insights(params)

        # Validate response data
        if not isinstance(data, (dict, list)):
            return jsonify({"error": "Invalid response format"}), 500

        return jsonify(data)

    except ValueError as e:
        security_logger.warning("Invalid parameters in organizations insights: %s", e)
        return jsonify({"error": "Invalid parameters"}), 400
    except Exception as e:
        security_logger.error("Error in organizations insights: %s", e)
        return jsonify({"error": "Failed to load organizations data"}), 500


@search_bp.route("/search")
@sanitize_params(sanitization_config)
@debug()
def search():
    """Main search endpoint with comprehensive security"""
    try:
        # Now you can use request.args.get() and request.args.getlist() directly
        # and they will return sanitized values
        query = request.args.get('q', '')
        selected_countries = request.args.getlist('country')
        selected_organizations = request.args.getlist('organization')
        selected_sources = request.args.getlist('source')
        offset = request.args.get('from', 0)
        days = request.args.get('date_posted_days', 365)

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
