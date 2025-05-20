from datetime import datetime
from flask import Flask, request, render_template
import requests
import bleach
from werkzeug.middleware.proxy_fix import ProxyFix
from markupsafe import escape

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

# Secure headers after every response
@app.after_request
def apply_secure_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "style-src 'self' https://cdn.jsdelivr.net; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data:;"
    )
    return response

OPENSEARCH_URL = "https://localhost:9200"
INDEX_NAME = "jobs"
AUTH = ('', '')

@app.template_filter('format_date')
def format_date(date_str):
    """
    Takes a date string in 'YYYY-MM-DD' and returns 'DD-MM-YY (X days ago)'
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        days_ago = (datetime.now() - date_obj).days
        ago_text = f"{days_ago} day{'s' if days_ago != 1 else ''} ago" if days_ago <= 30 else "30+ days ago"
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

@app.route("/", methods=["GET"])
def index():
    raw_query = request.args.get("q", "")
    query = sanitize_input(raw_query)

    try:
        offset = int(request.args.get('from', 0))
    except (ValueError, TypeError):
        offset = 0

    size = 20
    results = []
    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"
    total_results = 0

    if query:
        search_payload = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title", "description"]
                }
            },
            "from": offset,
            "size": size
        }

        try:
            res = requests.get(url=url, auth=AUTH, json=search_payload, verify=False, timeout=5)
            if res.status_code == 200:
                hits = res.json().get('hits', {}).get('hits', [])
                total_results = res.json().get('hits', {}).get('total', {}).get('value', 0)
                for hit in hits:
                    score = hit.get("_score", 0)
                    job = hit.get("_source", None)
                    if job:
                        job_details = {
                            "title": escape(job.get("title", "No Title")),
                            "description": fix_encoding(job.get("description", "")),
                            "country": escape(job.get("country", "").title()),
                            "organization": escape(job.get("organization", "").title()),
                            "url": escape(job.get("url", "")),
                            "date_posted": escape(job.get("date_posted", "")),
                            "score": round(score, 2)
                        }
                        results.append(job_details)
        except Exception as e:
            print("Search error:", str(e))

    selected_countries = [sanitize_input(c) for c in request.args.getlist('country')]

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_results.html', results=results)

    return render_template(
        "index.html",
        query=query,
        results=results,
        total_results=total_results,
        offset=offset,
        selected_countries=selected_countries
    )

if __name__ == '__main__':
    app.run(debug=True)
