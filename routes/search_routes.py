import time
import logging
from flask import Blueprint, render_template, request, jsonify, abort

from services.search_service import search_jobs
from utils.utils import get_date_range_days
from utils.security import (
    sanitize_input, validate_search_query,
    validate_filter_values, validate_request_size
)
from utils.monitoring import log_security_event

search = Blueprint('search', __name__)

security_logger = logging.getLogger('security')

@search.route("/search")
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
        days = int(request.args.get('date_posted_days', 365))
        if days < 0 or days > 365:  # Reasonable limits
            days = 365
    except (ValueError, TypeError):
        days = 365

    # Validate offset
    try:
        offset = int(request.args.get('from', 0))
        if offset < 0 or offset > 10000:  # Prevent excessive pagination
            offset = 0
    except (ValueError, TypeError):
        offset = 0

    date_range = None if days >= 31 else get_date_range_days(days)

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