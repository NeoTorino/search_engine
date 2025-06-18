import os
import json
import re
from collections import Counter
from datetime import datetime, timedelta
import requests

# Updated imports to match your security module structure
from security.core.validators import security_validator
from security.core.sanitizers import (
    unified_sanitizer, SanitizationConfig,
    SecurityLevel, sanitize_search_query
)
from security.engines.opensearch import sanitize_opensearch_query, validate_opensearch_aggregation
from security.monitoring.logging import log_security_event

OPENSEARCH_URL = "https://localhost:9200"
INDEX_NAME = "jobs"
AUTH = (os.getenv("USERNAME"), os.getenv("PASSWORD"))

def validate_search_query(query):
    """Wrapper function for search query validation using the new security validator"""
    if not query:
        return True, ""

    result = security_validator.validate_input(
        value=query,
        input_type='search',
        max_length=500
    )

    return result.is_valid, result.sanitized_value

def validate_filter_values(values, max_items=50):
    """Wrapper function for filter validation using the new security validator"""
    if not values:
        return []

    if not isinstance(values, list):
        values = [values]

    validated_values = []
    for value in values[:max_items]:  # Limit number of items
        result = security_validator.validate_input(
            value=value,
            input_type='filter',
            max_length=100
        )
        if result.is_valid and result.sanitized_value:
            validated_values.append(result.sanitized_value)

    return validated_values

def build_date_range_filter(date_posted_days):
    """Build date range filter for OpenSearch queries"""
    if not date_posted_days or not isinstance(date_posted_days, int):
        return None

    # Validate date range (1-365 days)
    if date_posted_days < 1 or date_posted_days > 365:
        return None

    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=date_posted_days)

        return {
            "gte": start_date.isoformat(),
            "lte": end_date.isoformat()
        }
    except Exception as e:
        log_security_event("DATE_FILTER_ERROR", f"Error building date filter: {e}")
        return None

def process_search_params(search_params):
    """Process and sanitize search parameters with comprehensive validation"""
    if not search_params or not isinstance(search_params, dict):
        return None, [], [], [], None

    try:
        # Validate and sanitize query
        query = search_params.get('query', '').strip()
        if query:
            is_valid, sanitized_query = validate_search_query(query)
            if not is_valid:
                log_security_event("INVALID_INSIGHTS_QUERY", f"Query: {query}")
                query = ""  # Invalid query, treat as empty
            else:
                query = sanitized_query

        # Process and validate filter parameters
        selected_countries = []
        if 'countries' in search_params:
            countries_raw = search_params.get('countries', [])
            selected_countries = validate_filter_values(countries_raw, max_items=20)

        selected_organizations = []
        if 'organizations' in search_params:
            orgs_raw = search_params.get('organizations', [])
            selected_organizations = validate_filter_values(orgs_raw, max_items=50)

        selected_sources = []
        if 'sources' in search_params:
            sources_raw = search_params.get('sources', [])
            selected_sources = validate_filter_values(sources_raw, max_items=10)

        # Build date range filter
        date_posted_days = search_params.get('date_posted_days')
        date_range = None
        if date_posted_days is not None:
            date_range = build_date_range_filter(date_posted_days)

        return query, selected_countries, selected_organizations, selected_sources, date_range

    except Exception as e:
        log_security_event("SEARCH_PARAMS_PROCESSING_ERROR", f"Error: {e}")
        return "", [], [], [], None

def build_filtered_query(query=None, selected_countries=None, selected_organizations=None, selected_sources=None, date_range=None):
    """Build a filtered query with comprehensive security validation"""
    try:
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
                clean_query = sanitize_search_query(query)
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

            # Add filters with validation using unified sanitizer
            config = SanitizationConfig(
                max_length=50,
                security_level=SecurityLevel.HIGH,
                preserve_case=True
            )

            if selected_countries and isinstance(selected_countries, list):
                safe_countries = []
                for country in selected_countries[:20]:  # Limit to 20 countries
                    clean_country = unified_sanitizer.sanitize(country, config)
                    if clean_country and len(clean_country) >= 2:
                        safe_countries.append(clean_country)

                if safe_countries:
                    bool_query["bool"]["filter"].append({"terms": {"country": safe_countries}})

            if selected_organizations and isinstance(selected_organizations, list):
                safe_orgs = []
                org_config = SanitizationConfig(
                    max_length=100,
                    security_level=SecurityLevel.HIGH,
                    preserve_case=True
                )
                for org in selected_organizations[:50]:  # Limit to 50 orgs
                    clean_org = unified_sanitizer.sanitize(org, org_config)
                    if clean_org and len(clean_org) >= 2:
                        safe_orgs.append(clean_org)

                if safe_orgs:
                    bool_query["bool"]["filter"].append({"terms": {"organization": safe_orgs}})

            if selected_sources and isinstance(selected_sources, list):
                safe_sources = []
                for source in selected_sources[:10]:  # Limit to 10 sources
                    clean_source = unified_sanitizer.sanitize(source, config)
                    if clean_source and len(clean_source) >= 2:
                        safe_sources.append(clean_source)

                if safe_sources:
                    bool_query["bool"]["filter"].append({"terms": {"source": safe_sources}})

            if date_range and isinstance(date_range, dict):
                bool_query["bool"]["filter"].append({"range": {"date_posted": date_range}})

            # Use the OpenSearch security engine to clean the final query
            return sanitize_opensearch_query(bool_query)

        return {"match_all": {}}

    except Exception as e:
        log_security_event("QUERY_BUILD_ERROR", f"Error building query: {e}")
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
        log_security_event("STOP_WORDS_LOAD_ERROR", f"Error: {e}")
        # Fallback to basic stop words
        return {
            'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were',
            'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'job', 'position', 'role', 'opportunity', 'vacancy'
        }

def get_combined_insights(search_params=None):
    """Get all insights data in a single response with comprehensive validation and security"""
    try:
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

        # 1. GET OVERVIEW STATISTICS
        try:
            count_payload = {"query": base_query} if base_query != {"match_all": {}} else {}
            # Clean the payload using OpenSearch security engine
            count_payload = sanitize_opensearch_query(count_payload)

            total_jobs_response = requests.get(
                f"{OPENSEARCH_URL}/{INDEX_NAME}/_count",
                auth=AUTH,
                json=count_payload,
                verify=False,
                timeout=10
            )

            total_jobs = 0
            if total_jobs_response.status_code == 200:
                total_jobs = total_jobs_response.json().get("count", 0)
            else:
                log_security_event("OPENSEARCH_ERROR", f"Count query failed: {total_jobs_response.status_code}")

            # Get unique organization count with the same filters
            org_query = {
                "size": 0,
                "query": base_query,
                "aggs": {
                    "unique_organizations": {
                        "cardinality": {"field": "organization"}
                    }
                }
            }
            # Clean the aggregation query
            org_query = sanitize_opensearch_query(org_query)
            org_query["aggs"] = validate_opensearch_aggregation(org_query.get("aggs", {}))

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
            else:
                log_security_event("OPENSEARCH_ERROR", f"Org aggregation failed: {org_response.status_code}")

            avg_jobs_per_org = round(total_jobs / total_organizations, 2) if total_organizations > 0 else 0

            insights_data["overview"] = {
                "total_jobs": int(total_jobs),
                "total_organizations": int(total_organizations),
                "avg_jobs_per_org": float(avg_jobs_per_org)
            }

        except Exception as overview_error:
            log_security_event("OVERVIEW_INSIGHTS_ERROR", f"Error: {overview_error}")

        # 2. GET JOBS PER DAY
        try:
            # Default to 365 days if no date range specified
            days = 365
            if date_range:
                # Extract days from date range if possible
                try:
                    start_date = datetime.fromisoformat(date_range['gte'].replace('Z', '+00:00'))
                    end_date = datetime.fromisoformat(date_range['lte'].replace('Z', '+00:00'))
                    days = min((end_date - start_date).days + 1, 365)  # Cap at 365 days
                except Exception:
                    days = 365

            # Calculate date range for aggregation
            end_date = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = end_date - timedelta(days=days-1)

            query_payload = {
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

            # Clean the query and aggregations
            query_payload = sanitize_opensearch_query(query_payload)
            query_payload["aggs"] = validate_opensearch_aggregation(query_payload.get("aggs", {}))

            response = requests.get(
                f"{OPENSEARCH_URL}/{INDEX_NAME}/_search",
                auth=AUTH,
                json=query_payload,
                verify=False,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                buckets = data.get("aggregations", {}).get("jobs_per_day", {}).get("buckets", [])

                dates = []
                counts = []

                for bucket in buckets:
                    try:
                        date_str = bucket["key_as_string"]
                        count = int(bucket["doc_count"])
                        formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m/%d")
                        dates.append(formatted_date)
                        counts.append(count)
                    except (ValueError, KeyError) as e:
                        log_security_event("DATE_PARSING_ERROR", f"Error parsing date: {e}")
                        continue

                insights_data["jobs_per_day"] = {
                    "dates": dates,
                    "counts": counts
                }
            else:
                log_security_event("OPENSEARCH_ERROR", f"Jobs per day query failed: {response.status_code}")

        except Exception as jobs_per_day_error:
            log_security_event("JOBS_PER_DAY_ERROR", f"Error: {jobs_per_day_error}")

        # 3. GET TOP COUNTRIES
        try:
            limit = 8  # Fixed limit for countries

            query_payload = {
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

            # Clean the query and aggregations
            query_payload = sanitize_opensearch_query(query_payload)
            query_payload["aggs"] = validate_opensearch_aggregation(query_payload.get("aggs", {}))

            response = requests.get(
                f"{OPENSEARCH_URL}/{INDEX_NAME}/_search",
                auth=AUTH,
                json=query_payload,
                verify=False,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                buckets = data.get("aggregations", {}).get("top_countries", {}).get("buckets", [])

                countries = []
                counts = []

                # Use unified sanitizer for country names
                config = SanitizationConfig(
                    max_length=50,
                    security_level=SecurityLevel.MEDIUM,
                    preserve_case=True
                )

                for bucket in buckets:
                    try:
                        country = unified_sanitizer.sanitize(bucket["key"], config)
                        count = int(bucket["doc_count"])
                        if country and count > 0:
                            countries.append(country.title())
                            counts.append(count)
                    except (ValueError, KeyError) as e:
                        log_security_event("COUNTRY_PARSING_ERROR", f"Error parsing country: {e}")
                        continue

                insights_data["top_countries"] = {
                    "countries": countries,
                    "counts": counts
                }
            else:
                log_security_event("OPENSEARCH_ERROR", f"Top countries query failed: {response.status_code}")

        except Exception as countries_error:
            log_security_event("TOP_COUNTRIES_ERROR", f"Error: {countries_error}")

        # 4. GET WORD CLOUD DATA
        try:
            limit = 50  # Fixed limit for word cloud
            stop_words = load_stop_words()

            # Limit the number of documents to process (prevent resource exhaustion)
            query_payload = {
                "size": min(5000, 10000),  # Reduced from 10000 for safety
                "_source": ["title", "description"],
                "query": base_query
            }

            # Clean the query
            query_payload = sanitize_opensearch_query(query_payload)

            response = requests.get(
                f"{OPENSEARCH_URL}/{INDEX_NAME}/_search",
                auth=AUTH,
                json=query_payload,
                verify=False,
                timeout=30
            )

            if response.status_code == 200:
                hits = response.json().get("hits", {}).get("hits", [])

                # Process text with security considerations using unified sanitizer
                all_words = []
                max_docs = min(len(hits), 5000)  # Process max 5000 documents

                # Configuration for text processing
                text_config = SanitizationConfig(
                    max_length=1000,
                    security_level=SecurityLevel.MEDIUM,
                    preserve_case=False,
                    strip_whitespace=True
                )

                for i, hit in enumerate(hits[:max_docs]):
                    try:
                        source = hit.get('_source', {})
                        title = unified_sanitizer.sanitize(source.get('title', ''),
                                                         SanitizationConfig(max_length=200, security_level=SecurityLevel.MEDIUM))
                        description = unified_sanitizer.sanitize(source.get('description', ''), text_config)

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

                    except Exception as word_error:
                        log_security_event("WORD_PROCESSING_ERROR", f"Error processing document {i}: {word_error}")
                        continue

                # Count words and get most common
                if all_words:
                    word_counts = Counter(all_words)
                    most_common = word_counts.most_common(limit)

                    word_config = SanitizationConfig(
                        max_length=50,
                        security_level=SecurityLevel.LOW,
                        preserve_case=True
                    )

                    insights_data["word_cloud"] = {
                        "words": [
                            {
                                "text": unified_sanitizer.sanitize(word.title(), word_config),
                                "count": int(count)
                            }
                            for word, count in most_common
                            if word and count > 0
                        ]
                    }
                else:
                    insights_data["word_cloud"] = {"words": []}

            else:
                log_security_event("OPENSEARCH_ERROR", f"Word cloud query failed: {response.status_code}")

        except Exception as word_cloud_error:
            log_security_event("WORD_CLOUD_ERROR", f"Error: {word_cloud_error}")

        return insights_data

    except Exception as e:
        log_security_event("COMBINED_INSIGHTS_ERROR", f"Error: {e}")
        return {
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

# Keep individual functions for backward compatibility if needed
def get_insights_overview(search_params=None):
    """Get overview statistics with comprehensive validation"""
    combined_data = get_combined_insights(search_params)
    return combined_data["overview"]

def get_jobs_per_day(search_params=None):
    """Get jobs posted per day with validation"""
    combined_data = get_combined_insights(search_params)
    return combined_data["jobs_per_day"]

def get_top_countries(search_params=None, limit=8):
    """Get top countries by job count with validation"""
    combined_data = get_combined_insights(search_params)
    return combined_data["top_countries"]

def get_word_cloud_data(search_params=None, limit=50):
    """Get word frequency data with comprehensive validation"""
    combined_data = get_combined_insights(search_params)
    return combined_data["word_cloud"]

def get_organizations_insights(search_params=None):
    """Get organizations with job counts and last update dates"""
    try:
        query, selected_countries, selected_organizations, selected_sources, date_range = process_search_params(search_params)
        base_query = build_filtered_query(query, selected_countries, selected_organizations, selected_sources, date_range)

        query_payload = {
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

        # Clean the query and aggregations
        query_payload = sanitize_opensearch_query(query_payload)
        query_payload["aggs"] = validate_opensearch_aggregation(query_payload.get("aggs", {}))

        response = requests.get(
            f"{OPENSEARCH_URL}/{INDEX_NAME}/_search",
            auth=AUTH,
            json=query_payload,
            verify=False,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            buckets = data.get("aggregations", {}).get("organizations", {}).get("buckets", [])

            organizations = []

            # Configuration for organization data sanitization
            org_config = SanitizationConfig(
                max_length=200,
                security_level=SecurityLevel.MEDIUM,
                preserve_case=True
            )

            url_config = SanitizationConfig(
                max_length=500,
                security_level=SecurityLevel.HIGH,
                preserve_case=True
            )

            for bucket in buckets:
                try:
                    org_name = unified_sanitizer.sanitize(bucket["key"], org_config)
                    job_count = int(bucket["job_count"]["value"])

                    # Validate and sanitize last updated date
                    last_updated = None
                    if bucket["last_updated"]["value"]:
                        last_updated = bucket["last_updated"]["value_as_string"]
                        # Basic date validation
                        if last_updated and len(last_updated) > 50:  # Prevent excessively long dates
                            last_updated = last_updated[:50]

                    # Extract and validate URL
                    url_careers_buckets = bucket.get("url_careers", {}).get("buckets", [])
                    url_careers = None
                    if url_careers_buckets:
                        raw_url = url_careers_buckets[0]["key"]
                        # Basic URL validation
                        if raw_url and isinstance(raw_url, str) and len(raw_url) < 500:
                            # Simple URL pattern check
                            if re.match(r'^https?://', raw_url):
                                url_careers = unified_sanitizer.sanitize(raw_url, url_config)

                    if org_name and job_count > 0:
                        organizations.append({
                            "name": org_name,
                            "job_count": job_count,
                            "last_updated": last_updated,
                            "url_careers": url_careers
                        })

                except Exception as org_error:
                    log_security_event("ORG_PROCESSING_ERROR", f"Error processing organization: {org_error}")
                    continue

            return {"organizations": organizations}
        else:
            log_security_event("OPENSEARCH_ERROR", f"Organizations query failed: {response.status_code}")
            return {"organizations": []}

    except Exception as e:
        log_security_event("ORGANIZATIONS_ERROR", f"Error: {e}")
        return {"organizations": []}
