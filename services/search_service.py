import os
import json
from markupsafe import escape
import requests
from lib.text_processing import fix_encoding, truncate_description

OPENSEARCH_URL = "https://localhost:9200"
INDEX_NAME = "jobs"
AUTH = (os.getenv("USERNAME"), os.getenv("PASSWORD"))

def is_not_blank(s: str) -> bool:
    return bool(s and not s.isspace())

def search_jobs(query, selected_countries=None, selected_organizations=None, selected_sources=None, date_range=None, offset=0, size=12):
    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"

    payload = {
        "from": offset,
        "size": size,
        "aggs": {
            "countries": {
                "terms": {"field": "country", "size": 100}
            },
            "organizations": {
                "terms": {"field": "organization", "size": 100}
            },
            "sources": {
                "terms": {"field": "source", "size": 100}
            }
        }
    }

    # Initialize query structure
    has_text_query = query and is_not_blank(query)
    has_filters = bool(selected_countries or selected_organizations or selected_sources or date_range)

    if has_text_query or has_filters:
        # Build bool query with must and filter clauses
        payload["query"] = {
            "bool": {
                "must": [],
                "filter": []
            }
        }

        # Add text search if query is not empty
        if has_text_query:
            payload["query"]["bool"]["must"].append({
                "multi_match": {"query": query, "fields": ["title"]}
            })

        # Add filters
        if selected_countries:
            payload["query"]["bool"]["filter"].append({"terms": {"country": selected_countries}})
        if selected_organizations:
            payload["query"]["bool"]["filter"].append({"terms": {"organization": selected_organizations}})
        if selected_sources:
            payload["query"]["bool"]["filter"].append({"terms": {"source": selected_sources}})
        if date_range:
            payload["query"]["bool"]["filter"].append({
                "range": {
                    "date_posted": {
                        "gte": date_range['start'].isoformat() if isinstance(date_range['start'], datetime) else date_range['start'],
                        "lte": date_range['end'].isoformat() if isinstance(date_range['end'], datetime) else date_range['end']
                    }
                }
            })

        # If we only have filters but no text query, add match_all to must clause
        if not has_text_query:
            payload["query"]["bool"]["must"].append({"match_all": {}})
    else:
        # No query and no filters - return everything
        payload["query"] = {"match_all": {}}

    results = []
    total_results = 0
    country_counts = {}
    organization_counts = {}
    source_counts = {}
    show_load_more = True

    try:
        print(json.dumps(payload, indent=4))    # for debugging
        res = requests.get(url, auth=AUTH, json=payload, verify=False, timeout=5)
        if res.status_code == 200:
            data = res.json()
            hits = data.get('hits', {}).get('hits', [])
            total_results = data.get('hits', {}).get('total', {}).get('value', 0)

            # Get country counts
            country_buckets = data.get('aggregations', {}).get('countries', {}).get('buckets', [])
            country_counts = dict(sorted((b["key"], b["doc_count"]) for b in country_buckets))

            # Get organization counts
            org_buckets = data.get('aggregations', {}).get('organizations', {}).get('buckets', [])
            organization_counts = dict(sorted((b["key"], b["doc_count"]) for b in org_buckets))

            # Get source counts
            source_buckets = data.get('aggregations', {}).get('sources', {}).get('buckets', [])
            source_counts = dict(sorted((b["key"], b["doc_count"]) for b in source_buckets))

            show_load_more = (offset + size) < total_results

            for hit in hits:
                job = hit.get("_source", {})
                results.append({
                    "title": escape(job.get("title", "No Title")),
                    "description": truncate_description(fix_encoding(job.get("summary", ""))),
                    "country": escape(job.get("country", "").title()),
                    "organization": escape(job.get("organization", "")),
                    "source": escape(job.get("source", "").title()),
                    "url": escape(job.get("url", "")),
                    "date_posted": escape(job.get("date_posted", ""))
                })
        else:
            print(f"Elasticsearch error: {res.status_code} - {res.text}")
    except Exception as e:
        print("Search error:", str(e))

    return results, total_results, country_counts, organization_counts, source_counts, show_load_more

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