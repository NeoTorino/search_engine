import os
import time
import json
from datetime import datetime, timedelta
from flask import Flask, request, render_template
import requests
import urllib3
import bleach
from werkzeug.middleware.proxy_fix import ProxyFix
from markupsafe import escape
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv(".env")

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

OPENSEARCH_URL = "https://localhost:9200"
INDEX_NAME = "jobs"
username = os.environ.get('USERNAME', None)
password = os.environ.get('PASSWORD', None)
AUTH = (username, password)

def get_date_range(filter_value):
    now = datetime.utcnow()
    if filter_value == 'today':
        return {'gte': now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()}
    elif filter_value == 'last_week':
        return {'gte': (now - timedelta(days=7)).isoformat()}
    elif filter_value == 'last_month':
        return {'gte': (now - timedelta(days=30)).isoformat()}
    elif filter_value == 'older':
        return {'lt': (now - timedelta(days=30)).isoformat()}
    return None

def truncate_description(text, limit=300):
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


# Secure headers after every response
@app.after_request
def apply_secure_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "img-src 'self' data:;"
        "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self' https://cdn.jsdelivr.net https://code.jquery.com https://unpkg.com; "
    )
    return response

@app.template_filter('format_date')
def format_date(date_str):
    """
    Takes a date string in 'YYYY-MM-DD' and returns 'DD-MM-YY (X days ago)'
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        days_ago = (datetime.now() - date_obj).days
        if days_ago == 0:
            ago_text = "Today"
        elif days_ago == 1:
            ago_text = "Yesterday"
        elif days_ago > 1 and days_ago <= 30:
            ago_text = f"{days_ago} days ago"
        else:
            ago_text = "30+ days ago"
        return f"{ago_text}"
    except Exception:
        return escape(date_str)  # Fallback to escaped string if parsing fails

def fix_encoding(text):
    if isinstance(text, bytes):
        return text.decode('utf-8', errors='replace')
    else:
        try:
            return text.encode('latin1').decode('utf-8')
        except Exception:
            return text

def sanitize_input(value):
    # Very basic HTML cleaner for user inputs
    return bleach.clean(value, tags=[], attributes={}, strip=True)


def get_landing_stats():
    url_orgs = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"
    url_count = f"{OPENSEARCH_URL}/{INDEX_NAME}/_count"

    search_payload = {
        "size": 0,  # we don't need actual hits
        "aggs": {
            "unique_orgs": {
                "cardinality": {
                    "field": "organization"
                }
            }
        }
    }

    total_jobs = 0
    total_orgs = 0

    try:
        response = requests.get(url=url_orgs, auth=AUTH, json=search_payload, verify=False, timeout=5)
        if response.status_code == 200:
            data = response.json()
            total_orgs = data.get("aggregations", {}).get("unique_orgs", {}).get("value", 0)
    except Exception as e:
        print("Landing stats error (orgs).", str(e))
    
    try:
        response = requests.get(url=url_count, auth=AUTH, verify=False, timeout=5)
        if response.status_code == 200:
            data = response.json()
            total_jobs = data.get("count", 0)
    except Exception as e:
        print("Landing stats error (jobs).", str(e))

    return total_jobs, total_orgs


def search_jobs(query, selected_countries=None, date_filter=None, offset=0, size=12):

    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"

    search_payload = {
        "from": offset,
        "size": size,
        "query": {
            "bool": {
                "must": [
                    {"multi_match": {"query": query, "fields": ["title"]}}
                ],
                "filter": []
            }
        },
        "aggs": {
            "countries": {
                "terms": {
                    "field": "country",
                    "size": 100
                }
            }
        }
    }

    total_results = 0
    show_load_more = True
    results = []
    country_counts = []

    # If country filters are applied
    if selected_countries:
        search_payload["query"]["bool"]["filter"].append({
            "terms": {"country": selected_countries}
        })
    
    # Date filter
    date_range = get_date_range(date_filter)
    if date_range:
        search_payload["query"]["bool"]["filter"].append({
            "range": {
                "date_posted": date_range
            }
        })

    try:
        #print(json.dumps(search_payload, indent=4))
        response = requests.get(url=url, auth=AUTH, json=search_payload, verify=False, timeout=5)
        if response.status_code == 200:
            data = response.json()
            hits = data.get('hits', {}).get('hits', [])
            total_results = data.get('hits', {}).get('total', {}).get('value', 0)
            country_buckets = data.get('aggregations', {}).get('countries', {}).get('buckets', {})

            # Country count mapping
            country_counts = dict(sorted(
                ((bucket["key"], bucket["doc_count"]) for bucket in country_buckets),
                key=lambda x: x[0].lower()
            ))

            # Determine if "Load More" button should show
            show_load_more = (offset + size) < total_results

            for hit in hits:
                #score = hit.get("_score", 0)
                job = hit.get("_source", None)
                if job:
                    job_details = {
                        "title": escape(job.get("title", "No Title")),
                        "description": truncate_description(fix_encoding(job.get("description", "No Description"))),
                        "country": escape(job.get("country", "No Country").title()),
                        "organization": escape(job.get("organization", "No Organization").title()),
                        "url": escape(job.get("url", "")),
                        "date_posted": escape(job.get("date_posted", ""))
                    }
                    results.append(job_details)
    except Exception as e:
        print("Search error:", str(e))

    return results, total_results, country_counts, show_load_more


@app.route("/", methods=["GET"])
def index():
    raw_query = request.args.get("q", "")
    query = sanitize_input(raw_query)

    try:
        offset = int(request.args.get('from', 0))
    except (ValueError, TypeError):
        offset = 0

    if query:
        selected_countries = [sanitize_input(c) for c in request.args.getlist('country')]
        date_filter = request.args.get('date_posted')
        results, total_results, country_counts, show_load_more = search_jobs(query, selected_countries, date_filter, offset)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render_template('_results.html', results=results)
        
        return render_template(
            "index.html",
            query=query,
            results=results,
            total_results=total_results,
            offset=offset,
            selected_countries=selected_countries,
            country_counts=country_counts,
            show_load_more=show_load_more,
            selected_date=date_filter,
            time=time
        )

    else:
        total_jobs, total_orgs = get_landing_stats()
        return render_template('index.html', total_jobs=total_jobs, total_orgs=total_orgs, time=time)

if __name__ == '__main__':
    app.run(debug=True)
