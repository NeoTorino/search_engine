import time
import json

from flask import Blueprint, render_template, request, jsonify
from services.utils import sanitize_input, get_date_range_days
from services.search_service import search_jobs, get_landing_stats
from services.stats_service import get_stats_overview, get_jobs_per_day, get_top_countries, get_word_cloud_data, get_organizations_stats

main = Blueprint('main', __name__)

@main.route("/", methods=["GET"])
def index():
    total_jobs, total_orgs = get_landing_stats()
    return render_template('index.html',
                            total_jobs=total_jobs,
                            total_orgs=total_orgs,
                            time=time)
    # Note: NO 'query' variable is passed here


@main.route("/search")
def search_results():
    raw_query = request.args.get("q", "")
    query = sanitize_input(raw_query) if raw_query else ""
    
    # Check if this is an empty query search request
    is_empty_query = not query or query.isspace()

    try:
        offset = int(request.args.get('from', 0))
    except (ValueError, TypeError):
        offset = 0

    try:
        days = int(request.args.get('date_posted_days', 30))
    except (ValueError, TypeError):
        days = 30

    date_range = None if days >= 30 else get_date_range_days(days)

    selected_countries = [sanitize_input(c) for c in request.args.getlist('country')]
    selected_organizations = [sanitize_input(o) for o in request.args.getlist('organization')]

    print(f"query: '{query}' (empty: {is_empty_query})")
    print(f"date_range: {date_range}")
    print(f"selected_countries: {selected_countries}")
    print(f"selected_organizations: {selected_organizations}")
    
    results, total_results, country_counts, organization_counts, show_load_more = search_jobs(
        query, selected_countries, selected_organizations, date_range, offset
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
            'show_load_more': show_load_more,
            'query': query,
            'is_empty_query': is_empty_query
        }
        return jsonify(response_data)

    # Always show search results page (even for empty queries)
    return render_template(
        'index.html',
        query=query,  # Always pass query variable (even if empty string)
        offset=offset,
        results=results,
        total_results=total_results,
        show_load_more=show_load_more,
        country_counts=country_counts or {},
        organization_counts=organization_counts or {},
        selected_countries=selected_countries or [],
        selected_organizations=selected_organizations or [],
        date_posted_days=days,
        is_empty_query=is_empty_query,  # Always pass this flag
        time=time
    )

@main.route("/about")
def about():
    return render_template("about.html", time=time)

@main.route("/contact")
def contact():
    return render_template("organizations.html",time=time)

@main.route("/organizations")
def organizations():
    return render_template("organizations.html", time=time)

@main.route("/sources")
def sources():
    return render_template("sources.html",nonce=g.csp_nonce, time=time)

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
        return jsonify({"error": "Failed to load overview stats"}), 500

@main.route("/api/stats/jobs-per-day")
def stats_jobs_per_day():
    """Get jobs posted per day for the last 30 days"""
    try:
        data = get_jobs_per_day()
        return jsonify(data)
    except Exception as e:
        print(f"Error in jobs per day: {e}")
        return jsonify({"error": "Failed to load jobs per day data"}), 500

@main.route("/api/stats/top-countries")
def stats_top_countries():
    """Get top countries by job count"""
    try:
        data = get_top_countries()
        return jsonify(data)
    except Exception as e:
        print(f"Error in top countries: {e}")
        return jsonify({"error": "Failed to load countries data"}), 500

@main.route("/api/stats/word-cloud")
def stats_word_cloud():
    """Get word frequency data for job titles"""
    try:
        data = get_word_cloud_data()
        return jsonify(data)
    except Exception as e:
        print(f"Error in word cloud: {e}")
        return jsonify({"error": "Failed to load word cloud data"}), 500

@main.route("/api/stats/organizations")
def stats_organizations():
    """Get organizations with job counts and last update dates"""
    try:
        data = get_organizations_stats()
        return jsonify(data)
    except Exception as e:
        print(f"Error in organizations stats: {e}")
        return jsonify({"error": "Failed to load organizations data"}), 500