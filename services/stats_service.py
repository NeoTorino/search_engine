import os
import json
import re
from collections import Counter
from datetime import datetime, timedelta
import requests

OPENSEARCH_URL = "https://localhost:9200"
INDEX_NAME = "jobs"
AUTH = (os.getenv("USERNAME"), os.getenv("PASSWORD"))

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

def get_word_cloud_data(limit=50):
    """Get word frequency data from job titles"""
    try:
        # Get all job titles
        query = {
            "size": 10000,  # Adjust based on your data size
            "_source": ["title"],
            "query": {
                "match_all": {}
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
            hits = data.get("hits", {}).get("hits", [])
            
            # Extract titles and process them
            titles = []
            for hit in hits:
                title = hit.get("_source", {}).get("title", "")
                if title:
                    titles.append(title)
            
            # Process titles to extract words
            all_words = []
            
            # Common stop words to exclude
            stop_words = {
                'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 
                'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were',
                'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                'would', 'could', 'should', 'may', 'might', 'must', 'can', 'shall',
                'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
                'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
                'his', 'her', 'its', 'our', 'their', '&', '-', '/', '|', '–',
                'job', 'position', 'role', 'opportunity', 'vacancy'
            }
            
            for title in titles:
                # Clean and split the title
                # Remove special characters and convert to lowercase
                cleaned_title = re.sub(r'[^\w\s]', ' ', title.lower())
                words = cleaned_title.split()
                
                # Filter words
                for word in words:
                    word = word.strip()
                    # Only include words that are 2+ characters and not stop words
                    if len(word) >= 2 and word not in stop_words and word.isalpha():
                        all_words.append(word)
            
            # Count word frequency
            word_counts = Counter(all_words)
            most_common = word_counts.most_common(limit)
            
            # Format for frontend
            words_data = []
            for word, count in most_common:
                words_data.append({
                    "text": word.title(),
                    "count": count
                })
            
            return {"words": words_data}
        else:
            print(f"Error response from OpenSearch: {response.status_code} - {response.text}")
            return {"words": []}
            
    except Exception as e:
        print(f"Error in get_word_cloud_data: {e}")
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
                        "size": 1000,  # Adjust based on your data
                        "order": {"job_count": "desc"}
                    },
                    "aggs": {
                        "job_count": {
                            "value_count": {"field": "organization"}
                        },
                        "last_updated": {
                            "max": {"field": "last_update"}
                        },
                        "country": {
                            "terms": {
                                "field": "country",
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
                
                # Get the most common country for this organization
                country_buckets = bucket.get("country", {}).get("buckets", [])
                country = country_buckets[0]["key"] if country_buckets else None
                
                organizations.append({
                    "name": org_name,
                    "job_count": job_count,
                    "last_updated": last_updated,
                    "country": country
                })
            
            return {"organizations": organizations}
        else:
            print(f"Error response from OpenSearch: {response.status_code} - {response.text}")
            return {"organizations": []}
            
    except Exception as e:
        print(f"Error in get_organizations_stats: {e}")
        return {"organizations": []}