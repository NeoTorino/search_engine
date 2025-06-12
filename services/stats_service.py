import os
import json
import re
from collections import Counter
from datetime import datetime, timedelta
import requests

OPENSEARCH_URL = "https://localhost:9200"
INDEX_NAME = "jobs"
AUTH = (os.getenv("USERNAME"), os.getenv("PASSWORD"))

def load_stop_words():
    """Load stop words from JSON file"""
    try:
        # Get the directory where this script is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        stop_words_file = os.path.join(current_dir, 'stop_words_english.json')
        
        with open(stop_words_file, 'r', encoding='utf-8') as f:
            stop_words_list = json.load(f)
            # Convert to set for faster lookup and add some job-specific stop words
            stop_words = set(stop_words_list + [
                'job', 'position', 'role', 'opportunity', 'vacancy', '&', '-', '/', '|', '–'
            ])
            return stop_words
    except Exception as e:
        print(f"Error loading stop words: {e}")
        # Fallback to basic stop words if file loading fails
        return {
            'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were',
            'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'job', 'position', 'role', 'opportunity', 'vacancy'
        }

def get_stats_overview():
    """Get overview statistics: total jobs, organizations, average jobs per org"""
    try:
        # Get total job count
        total_jobs_response = requests.get(
            f"{OPENSEARCH_URL}/{INDEX_NAME}/_count",
            auth=AUTH,
            verify=False,
            timeout=10
        )
        
        total_jobs = 0
        if total_jobs_response.status_code == 200:
            total_jobs = total_jobs_response.json().get("count", 0)
        
        # Get unique organization count
        org_query = {
            "size": 0,
            "aggs": {
                "unique_organizations": {
                    "cardinality": {"field": "organization"}
                }
            }
        }
        
        org_response = requests.get(
            f"{OPENSEARCH_URL}/{INDEX_NAME}/_search",
            auth=AUTH,
            json=org_query,
            verify=False,
            timeout=10
        )
        
        total_organizations = 0
        if org_response.status_code == 200:
            total_organizations = org_response.json().get("aggregations", {}).get("unique_organizations", {}).get("value", 0)
        
        avg_jobs_per_org = total_jobs / total_organizations if total_organizations > 0 else 0
        
        return {
            "total_jobs": total_jobs,
            "total_organizations": total_organizations,
            "avg_jobs_per_org": avg_jobs_per_org
        }
        
    except Exception as e:
        print(f"Error in get_stats_overview: {e}")
        return {
            "total_jobs": 0,
            "total_organizations": 0,
            "avg_jobs_per_org": 0
        }

def get_jobs_per_day(days=30):
    """Get jobs posted per day for the last N days"""
    try:
        # Calculate date range
        end_date = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
        start_date = end_date - timedelta(days=days-1)
        
        query = {
            "size": 0,
            "query": {
                "range": {
                    "date_posted": {
                        "gte": start_date.isoformat(),
                        "lte": end_date.isoformat()
                    }
                }
            },
            "aggs": {
                "jobs_per_day": {
                    "date_histogram": {
                        "field": "date_posted",
                        "calendar_interval": "day",
                        "format": "yyyy-MM-dd",
                        "order": {"_key": "asc"}
                    }
                }
            }
        }
        
        response = requests.get(
            f"{OPENSEARCH_URL}/{INDEX_NAME}/_search",
            auth=AUTH,
            json=query,
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            buckets = data.get("aggregations", {}).get("jobs_per_day", {}).get("buckets", [])
            
            dates = []
            counts = []
            
            for bucket in buckets:
                date_str = bucket["key_as_string"]
                count = bucket["doc_count"]
                dates.append(datetime.strptime(date_str, "%Y-%m-%d").strftime("%m/%d"))
                counts.append(count)
            
            return {
                "dates": dates,
                "counts": counts
            }
        else:
            print(f"Error response from OpenSearch: {response.status_code} - {response.text}")
            return {"dates": [], "counts": []}
            
    except Exception as e:
        print(f"Error in get_jobs_per_day: {e}")
        return {"dates": [], "counts": []}

def get_top_countries(limit=8):
    """Get top countries by job count"""
    try:
        query = {
            "size": 0,
            "aggs": {
                "top_countries": {
                    "terms": {
                        "field": "country",
                        "size": limit,
                        "order": {"_count": "desc"}
                    }
                }
            }
        }
        
        response = requests.get(
            f"{OPENSEARCH_URL}/{INDEX_NAME}/_search",
            auth=AUTH,
            json=query,
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            buckets = data.get("aggregations", {}).get("top_countries", {}).get("buckets", [])
            
            countries = []
            counts = []
            
            for bucket in buckets:
                countries.append(bucket["key"].title())
                counts.append(bucket["doc_count"])
            
            return {
                "countries": countries,
                "counts": counts
            }
        else:
            print(f"Error response from OpenSearch: {response.status_code} - {response.text}")
            return {"countries": [], "counts": []}
            
    except Exception as e:
        print(f"Error in get_top_countries: {e}")
        return {"countries": [], "counts": []}

def get_word_cloud_data(limit=50, search_term=""):
    try:
        stop_words = load_stop_words()

        if search_term:
            query = {
                "size": 10000,
                "_source": ["title", "description"],
                "query": {
                    "match": {
                        "title": {
                            "query": search_term,
                            "operator": "and"
                        }
                    }
                }
            }
        else:
            query = {
                "size": 10000,
                "_source": ["title", "description"],
                "query": {"match_all": {}}
            }

        response = requests.get(
            f"{OPENSEARCH_URL}/{INDEX_NAME}/_search",
            auth=AUTH,
            json=query,
            verify=False,
            timeout=30
        )

        if response.status_code == 200:
            hits = response.json().get("hits", {}).get("hits", [])
            texts = [
                f"{hit['_source'].get('title', '')} {hit['_source'].get('description', '')}"
                for hit in hits
            ]
            
            all_words = []
            for text in texts:
                cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
                words = cleaned.split()
                for word in words:
                    if len(word) > 2 and word not in stop_words and word.isalpha():
                        all_words.append(word)

            word_counts = Counter(all_words)
            most_common = word_counts.most_common(limit)

            return {
                "words": [{"text": word.title(), "count": count} for word, count in most_common]
            }

        print(f"OpenSearch error: {response.status_code} - {response.text}")
        return {"words": []}

    except Exception as e:
        print(f"Exception in get_word_cloud_data: {e}")
        return {"words": []}


def get_organizations_stats():
    """Get organizations with job counts and last update dates"""
    try:
        query = {
            "size": 0,
            "aggs": {
                "organizations": {
                    "terms": {
                        "field": "organization",
                        "size": 5000,
                        "order": {"job_count": "desc"}
                    },
                    "aggs": {
                        "job_count": {
                            "value_count": {"field": "organization"}
                        },
                        "last_updated": {
                            "max": {"field": "last_update"}
                        },
                        "url_careers": {
                            "terms": {
                                "field": "url_careers",
                                "size": 1
                            }
                        }
                    }
                }
            }
        }
        
        response = requests.get(
            f"{OPENSEARCH_URL}/{INDEX_NAME}/_search",
            auth=AUTH,
            json=query,
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            buckets = data.get("aggregations", {}).get("organizations", {}).get("buckets", [])
            
            organizations = []
            for bucket in buckets:
                org_name = bucket["key"]
                job_count = bucket["job_count"]["value"]
                last_updated = bucket["last_updated"]["value_as_string"] if bucket["last_updated"]["value"] else None

                # Extract the first url_careers from the aggregation
                url_careers_buckets = bucket.get("url_careers", {}).get("buckets", [])
                url_careers = url_careers_buckets[0]["key"] if url_careers_buckets else None
                
                organizations.append({
                    "name": org_name,
                    "job_count": job_count,
                    "last_updated": last_updated,
                    "url_careers": url_careers
                })
            
            return {"organizations": organizations}
        else:
            print(f"Error response from OpenSearch: {response.status_code} - {response.text}")
            return {"organizations": []}
            
    except Exception as e:
        print(f"Error in get_organizations_stats: {e}")
        return {"organizations": []}