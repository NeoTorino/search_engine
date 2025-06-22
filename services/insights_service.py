import os
import json
import re
from collections import Counter
from datetime import datetime, timedelta
import requests

from utils.sanitizers import sanitize_element
from utils.general_utils import is_valid_date_format

OPENSEARCH_URL = "https://localhost:9200"
INDEX_NAME = "jobs"
AUTH = (os.getenv("USERNAME"), os.getenv("PASSWORD"))

def build_date_range_filter(date_posted_days):
    """Build date range filter for OpenSearch queries"""
    if not date_posted_days or not isinstance(date_posted_days, int):
        return None

    if date_posted_days < 1 or date_posted_days > 30:
        # we return everything in the last year if date_posted is >30
        date_posted_days = 365

    end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = (end_date - timedelta(days=date_posted_days)).replace(hour=0, minute=0, second=0, microsecond=0)

    return {
        "gte": start_date.isoformat(),
        "lte": end_date.isoformat()
    }

def process_search_params(search_params):
    """Process and sanitize search parameters with comprehensive validation"""
    clean_query = None
    clean_countries = []
    clean_organizations = []
    clean_sources = []
    clean_date_range = None

    if search_params and isinstance(search_params, dict):

        # Validate and sanitize query
        raw_query = search_params.get('q', '').strip()
        if raw_query:
            clean_query = sanitize_element(element=raw_query, default_value='')

        # Process and validate filter parameters
        raw_countries = search_params.get('countries', [])
        if raw_countries:
            clean_countries = sanitize_element(raw_countries)

        raw_organizations = search_params.get('organizations', [])
        if raw_organizations:
            clean_organizations = sanitize_element(raw_organizations)

        raw_sources = search_params.get('sources', [])
        if raw_sources:
            clean_sources = sanitize_element(element=raw_sources)

        # Build date range filter
        raw_date_posted_days = search_params.get('date_posted_days', None)
        if raw_date_posted_days:
            clean_date_posted_days = sanitize_element(raw_date_posted_days, default_value=365, min_value=0, max_value=365)
            clean_date_range = build_date_range_filter(clean_date_posted_days)

    return clean_query, clean_countries, clean_organizations, clean_sources, clean_date_range


def build_filtered_query(query=None, selected_countries=None, selected_organizations=None, selected_sources=None, date_range=None):
    """Build a filtered query with comprehensive security validation"""

    has_text_query = query and query.strip()
    has_filters = bool(selected_countries or selected_organizations or selected_sources or date_range)

    if has_text_query or has_filters:
        bool_query = {
            "bool": {
                "must": [],
                "filter": []
            }
        }

        # Add text search if query is not empty
        if has_text_query:
            # Double sanitize query for extra safety
            clean_query = sanitize_element(query)
            if clean_query:
                bool_query["bool"]["must"].append({
                    "multi_match": {
                        "query": clean_query,
                        "fields": ["title"]
                    }
                })
            else:
                bool_query["bool"]["must"].append({"match_all": {}})
        else:
            bool_query["bool"]["must"].append({"match_all": {}})

        if selected_countries and isinstance(selected_countries, list):
            safe_countries = sanitize_element(element=selected_countries, default_value=[])
            if safe_countries:
                bool_query["bool"]["filter"].append({"terms": {"country": safe_countries}})

        if selected_organizations and isinstance(selected_organizations, list):
            safe_orgs = sanitize_element(element=selected_organizations, default_value=[])
            if safe_orgs:
                bool_query["bool"]["filter"].append({"terms": {"organization": safe_orgs}})

        if selected_sources and isinstance(selected_sources, list):
            safe_sources = sanitize_element(element=selected_sources, default_value=[])
            if safe_sources:
                bool_query["bool"]["filter"].append({"terms": {"source": safe_sources}})

        if date_range and isinstance(date_range, dict):
            bool_query["bool"]["filter"].append({"range": {"date_posted": date_range}})

        return bool_query

    return {"match_all": {}}


def load_stop_words():
    """Load stop words from JSON file with error handling"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        stop_words_file = os.path.join(current_dir, 'stop_words_english.json')

        with open(stop_words_file, 'r', encoding='utf-8') as f:
            stop_words_list = json.load(f)
            # Convert to set for faster lookup and add job-specific stop words
            stop_words = set(stop_words_list + [
                'job', 'position', 'role', 'opportunity', 'vacancy',
                '&', '-', '/', '|', '–', 'the', 'and', 'or', 'for', 'with'
            ])
            return stop_words
    except Exception as e:
        # Fallback to basic stop words
        return {
            'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were',
            'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'job', 'position', 'role', 'opportunity', 'vacancy'
        }

def get_combined_insights(search_params=None):
    """Get all insights data in a single response with comprehensive validation and security"""
    query, selected_countries, selected_organizations, selected_sources, date_range = process_search_params(search_params)

    # Build the base query for filtering - this will be used for ALL insights
    base_query = build_filtered_query(query, selected_countries, selected_organizations, selected_sources, date_range)

    # Initialize response structure
    insights_data = {
        "overview": {
            "total_jobs": 0,
            "total_organizations": 0,
            "avg_jobs_per_org": 0
        },
        "jobs_per_day": {
            "dates": [],
            "counts": []
        },
        "top_countries": {
            "countries": [],
            "counts": []
        },
        "word_cloud": {
            "words": []
        }
    }

    url_search = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"
    url_count = f"{OPENSEARCH_URL}/{INDEX_NAME}/_count"

    # 1. GET OVERVIEW STATISTICS
    payload = {"query": base_query} if base_query != {"match_all": {}} else {}

    total_jobs_response = requests.get(url=url_count, auth=AUTH, json=payload, verify=False, timeout=10)

    total_jobs = 0
    if total_jobs_response.status_code == 200:
        total_jobs = total_jobs_response.json().get("count", 0)

    # Get unique organization count with the same filters
    payload = {
        "size": 0,
        "query": base_query,
        "aggs": {
            "unique_organizations": {
                "cardinality": {"field": "organization"}
            }
        }
    }

    response = requests.get(url=url_search, auth=AUTH, json=payload, verify=False, timeout=10)

    total_organizations = 0
    if response.status_code == 200:
        total_organizations = response.json().get("aggregations", {}).get("unique_organizations", {}).get("value", 0)

    avg_jobs_per_org = round(total_jobs / total_organizations, 2) if total_organizations > 0 else 0

    insights_data["overview"] = {
        "total_jobs": int(total_jobs),
        "total_organizations": int(total_organizations),
        "avg_jobs_per_org": float(avg_jobs_per_org)
    }

    # 2. GET JOBS PER DAY
    # Default to 365 days if no date range specified
    days = 365
    if date_range:
        # Extract days from date range if possible
        start_date = datetime.fromisoformat(date_range['gte'].replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(date_range['lte'].replace('Z', '+00:00'))
        days = min((end_date - start_date).days + 1, 365)  # Cap at 365 days

    # Calculate date range for aggregation
    end_date = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
    start_date = end_date - timedelta(days=days-1)

    payload = {
        "size": 0,
        "query": {
            "bool": {
                "must": [base_query],
                "filter": [{
                    "range": {
                        "date_posted": {
                            "gte": start_date.isoformat(),
                            "lte": end_date.isoformat()
                        }
                    }
                }]
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

    response = requests.get(url=url_search, auth=AUTH, json=payload, verify=False, timeout=10)

    if response.status_code == 200:
        data = response.json()
        buckets = data.get("aggregations", {}).get("jobs_per_day", {}).get("buckets", [])

        dates = []
        counts = []

        for bucket in buckets:
            raw_date_str = bucket.get("key_as_string", None)
            if raw_date_str:
                clean_date_str = raw_date_str if is_valid_date_format(raw_date_str) else sanitize_element(raw_date_str)
                if clean_date_str:
                    doc_count = bucket.get("doc_count", 0)
                    if doc_count and isinstance(doc_count, int) and doc_count >0:
                        formatted_date = datetime.strptime(clean_date_str, "%Y-%m-%d").strftime("%m/%d")
                        dates.append(formatted_date)
                        counts.append(doc_count)

        insights_data["jobs_per_day"] = {
            "dates": dates,
            "counts": counts
        }

    # 3. GET TOP COUNTRIES
    limit = 8  # Fixed limit for countries

    payload = {
        "size": 0,
        "query": base_query,
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

    response = requests.get(url=url_search, auth=AUTH, json=payload, verify=False, timeout=10)

    if response.status_code == 200:
        data = response.json()
        buckets = data.get("aggregations", {}).get("top_countries", {}).get("buckets", [])

        countries = []
        counts = []

        for bucket in buckets:
            raw_country = bucket.get("key", None)
            if raw_country:
                clean_country = sanitize_element(raw_country)
                if clean_country:
                    doc_count = bucket.get("doc_count", 0)
                    if doc_count and isinstance(doc_count, int) and doc_count >0:
                        countries.append(clean_country.title())
                        counts.append(doc_count)

        insights_data["top_countries"] = {
            "countries": countries,
            "counts": counts
        }

    # 4. GET WORD CLOUD DATA
    limit = 50  # Fixed limit for word cloud
    stop_words = load_stop_words()

    # Limit the number of documents to process (prevent resource exhaustion)
    payload = {
        "size": min(5000, 10000),  # Reduced from 10000 for safety
        "_source": ["title", "description"],
        "query": base_query
    }

    response = requests.get(url=url_search, auth=AUTH, json=payload, verify=False, timeout=10)

    if response.status_code == 200:
        hits = response.json().get("hits", {}).get("hits", [])

        # Process text with security considerations using unified sanitizer
        all_words = []
        max_docs = min(len(hits), 5000)  # Process max 5000 documents

        for hit in hits[:max_docs]:
            source = hit.get('_source', {})
            title = sanitize_element(source.get('title', ''))
            description = sanitize_element(source.get('description', ''))

            text = f"{title} {description}"

            # Clean and tokenize text
            # Remove extra whitespace and normalize
            text = re.sub(r'\s+', ' ', text.lower().strip())

            # Remove punctuation but keep letters and spaces
            cleaned = re.sub(r'[^\w\s]', ' ', text)

            # Split into words
            words = cleaned.split()

            for word in words:
                # Additional validation for each word
                if (len(word) > 2 and
                    len(word) < 50 and  # Prevent extremely long words
                    word not in stop_words and
                    word.isalpha() and
                    not re.search(r'(script|javascript|eval|exec)', word, re.IGNORECASE)):
                    all_words.append(word)


        # Count words and get most common
        if all_words:
            word_counts = Counter(all_words)
            most_common = word_counts.most_common(limit)

            insights_data["word_cloud"] = {
                "words": [
                    {
                        "text": sanitize_element(word.title()),
                        "count": int(count)
                    }
                    for word, count in most_common
                    if word and count > 0
                ]
            }
        else:
            insights_data["word_cloud"] = {"words": []}

    return insights_data


def get_organizations_insights(search_params=None):
    """Get organizations with job counts and last update dates"""

    query, selected_countries, selected_organizations, selected_sources, date_range = process_search_params(search_params)
    base_query = build_filtered_query(query, selected_countries, selected_organizations, selected_sources, date_range)

    payload = {
        "size": 0,
        "query": base_query,
        "aggs": {
            "organizations": {
                "terms": {
                    "field": "organization",
                    "size": min(1000, 5000),  # Reduced from 5000 for safety
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

    url_search = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"
    response = requests.get(url=url_search, auth=AUTH, json=payload, verify=False, timeout=10)

    if response.status_code == 200:
        data = response.json()
        buckets = data.get("aggregations", {}).get("organizations", {}).get("buckets", [])

        organizations = []

        for bucket in buckets:
            job_count = 0
            raw_org_name = bucket.get("key", None)
            if raw_org_name:
                clean_org_name = sanitize_element(raw_org_name)
                if clean_org_name:
                    job_count = bucket.get("job_count", {}).get("value", 0)

            # Validate and sanitize last updated date
            clean_last_updated = None
            value = bucket.get("last_updated", {}).get("value", None)
            if value:
                raw_last_updated = bucket.get("last_updated", {}).get("value_as_string", None)
                # Basic date validation
                if raw_last_updated :
                    clean_last_updated = sanitize_element(raw_last_updated)

            # Extract and validate URL
            url_careers_buckets = bucket.get("url_careers", {}).get("buckets", [])
            url_careers = None
            if url_careers_buckets:
                raw_url = url_careers_buckets[0].get("key", None)
                # Basic URL validation
                if raw_url:
                    clean_url = sanitize_element(element=raw_url, default_value=None, limit=(0, 500), hint='url')
                    if clean_url and isinstance(clean_url, str) and len(clean_url) < 500:
                    # Simple URL pattern check
                        if re.match(r'^https?://', clean_url):
                            url_careers = clean_url

            if clean_org_name and job_count > 0:
                organizations.append({
                    "name": clean_org_name,
                    "job_count": job_count,
                    "last_updated": clean_last_updated,
                    "url_careers": url_careers
                })

        return {"organizations": organizations}
