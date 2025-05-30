import os
import requests


OPENSEARCH_URL = "https://localhost:9200"
INDEX_NAME = "jobs"
AUTH = (os.getenv("USERNAME"), os.getenv("PASSWORD"))

def get_all_organizations(query=None):
    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"
    
    payload = {
        "size": 0,
        "aggs": {
            "organizations": {
                "terms": {
                    "field": "organization",
                    "size": 200,
                    "order": {"_key": "asc"}
                }
            }
        }
    }

    if query and isinstance(query, str):
        payload["query"] = {
            "bool": {
                "must": [{"multi_match": {"query": query, "fields": ["title"]}}],
                "filter": []
            }
        }

    try:
        res = requests.get(url, auth=AUTH, json=payload, verify=False, timeout=5)
        if res.status_code == 200:
            buckets = res.json().get('aggregations', {}).get('organizations', {}).get('buckets', [])
            return [{
                "value": b["key"].lower(),
                "label": f"{b['key'].title()} ({b['doc_count']})",
                "count": b["doc_count"]
            } for b in buckets]
    except Exception as e:
        print("Error fetching organizations:", str(e))
    return []