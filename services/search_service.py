import os
import json
from datetime import datetime, timedelta
from markupsafe import escape
import requests
from services.utils import fix_encoding, truncate_description

OPENSEARCH_URL = "https://localhost:9200"
INDEX_NAME = "jobs"
AUTH = (os.getenv("USERNAME"), os.getenv("PASSWORD"))

def search_jobs(query, selected_countries=None, date_range=None, offset=0, size=12):
    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"

    payload = {
        "from": offset,
        "size": size,
        "query": {
            "bool": {
                "must": [{"multi_match": {"query": query, "fields": ["title"]}}],
                "filter": []
            }
        },
        "aggs": {
            "countries": {
                "terms": {"field": "country", "size": 100}
            }
        }
    }

    if selected_countries:
        payload["query"]["bool"]["filter"].append({"terms": {"country": selected_countries}})
    if date_range:
        payload["query"]["bool"]["filter"].append({"range": {"date_posted": date_range}})

    results, total_results, country_counts, show_load_more = [], 0, {}, True

    try:
        print(json.dumps(payload, indent=4))
        res = requests.get(url, auth=AUTH, json=payload, verify=False, timeout=5)
        if res.status_code == 200:
            data = res.json()
            hits = data.get('hits', {}).get('hits', [])
            total_results = data.get('hits', {}).get('total', {}).get('value', 0)
            buckets = data.get('aggregations', {}).get('countries', {}).get('buckets', [])
            country_counts = dict(sorted((b["key"], b["doc_count"]) for b in buckets))
            show_load_more = (offset + size) < total_results

            for hit in hits:
                job = hit.get("_source", {})
                results.append({
                    "title": escape(job.get("title", "No Title")),
                    "description": truncate_description(fix_encoding(job.get("description", ""))),
                    "country": escape(job.get("country", "").title()),
                    "organization": escape(job.get("organization", "").title()),
                    "url": escape(job.get("url", "")),
                    "date_posted": escape(job.get("date_posted", ""))
                })
    except Exception as e:
        print("Search error:", str(e))

    return results, total_results, country_counts, show_load_more

def get_landing_stats():
    stats = {"jobs": 0, "orgs": 0}
    try:
        res_org = requests.get(f"{OPENSEARCH_URL}/{INDEX_NAME}/_search", auth=AUTH, json={
            "size": 0, "aggs": {"unique_orgs": {"cardinality": {"field": "organization"}}}
        }, verify=False, timeout=5)
        if res_org.status_code == 200:
            stats["orgs"] = res_org.json().get("aggregations", {}).get("unique_orgs", {}).get("value", 0)
        
        res_jobs = requests.get(f"{OPENSEARCH_URL}/{INDEX_NAME}/_count", auth=AUTH, verify=False, timeout=5)
        if res_jobs.status_code == 200:
            stats["jobs"] = res_jobs.json().get("count", 0)
    except Exception as e:
        print("Landing stats error:", str(e))
    return stats["jobs"], stats["orgs"]
