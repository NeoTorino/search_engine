import time
import json

from flask import Blueprint, render_template, request, jsonify
from services.utils import sanitize_input, get_date_range_days
from services.search_service import search_jobs, get_landing_stats
from services.country_service import get_all_countries
from services.organization_service import get_all_organizations

main = Blueprint('main', __name__)

@main.route("/api/countries", methods=["GET"])
def api_countries():
    countries = get_all_countries()
    return jsonify(countries)

@main.route("/api/organizations", methods=["GET"])
def api_organizations():
    organizations = get_all_organizations()
    return jsonify(organizations)

@main.route("/", methods=["GET"])
def index():
    total_jobs, total_orgs = get_landing_stats()
    return render_template('index.html',
                            total_jobs=total_jobs,
                            total_orgs=total_orgs,
                            time=time)

@main.route("/search")
def search_results():

    raw_query = request.args.get("q", "")
    query = sanitize_input(raw_query)

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

    print(f"date_range: {date_range}")
    print(f"selected_countries: {selected_countries}")
    print(f"selected_organizations: {selected_organizations}")
    results, total_results, country_counts, organization_counts, show_load_more = search_jobs(
        query, selected_countries, selected_organizations, date_range, offset
    )
    print(f"total_results: {total_results}")
    print("-" * 40)

    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # For load more requests, only return the HTML results
        if offset > 0:
            rendered_results = render_template('_results.html', results=results)
            return rendered_results
        
        # For filter changes (offset = 0), return JSON with metadata
        rendered_results = render_template('_results.html', results=results)
        
        response_data = {
            'html': rendered_results,
            'total_results': total_results,
            'country_counts': country_counts or {},
            'organization_counts': organization_counts or {},
            'show_load_more': show_load_more,
            'query': query
        }
        return jsonify(response_data)

    return render_template(
        'index.html',
        query=query,
        offset=offset,
        results=results,
        total_results=total_results,
        show_load_more=show_load_more,
        country_counts=country_counts or {},
        organization_counts=organization_counts or {},
        selected_countries=selected_countries or [],
        selected_organizations=selected_organizations or [],
        date_posted_days=days,
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

@main.route("/stats")
def stats():
    return render_template("stats.html", time=time)

@main.route("/sources")
def sources():
    return render_template("sources.html",nonce=g.csp_nonce, time=time)