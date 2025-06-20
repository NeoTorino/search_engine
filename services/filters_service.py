import os
import logging
import requests

from utils.sanitizers import sanitize_element

OPENSEARCH_URL = "https://localhost:9200"
INDEX_NAME = "jobs"
AUTH = (os.getenv("USERNAME"), os.getenv("PASSWORD"))

MAX_LIST_COUNTRY = 150
MAX_LIST_ORGANIZATION = 5000
MAX_LIST_SOURCE = 50


def req_aggs(fields: dict[str, int]):
    """
    Request OpenSearch aggregations for specified fields with sizes.

    Args:
        fields (dict): Mapping of field names to aggregation sizes

    Returns:
        dict: Aggregation results
    """
    aggs = {
        field: {
            "terms": {
                "field": field,
                "size": min(size, 10000),
                "order": {"_count": "desc"}
            }
        }
        for field, size in fields.items()
    }

    payload = {
        "size": 0,
        "aggs": aggs
    }

    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"
    try:
        response = requests.get(url=url, auth=AUTH, json=payload, verify=False, timeout=30)
        if response.status_code == 200:
            return response.json().get("aggregations", {})
    except requests.RequestException as e:
        logging.warning("OpenSearch aggregation request failed: %s", e)
    return {}


def parse_buckets(buckets):
    """
    Extract and sanitize values from aggregation buckets.

    Args:
        buckets (list): List of aggregation buckets

    Returns:
        set: Sanitized set of values
    """
    results = set()
    for bucket in buckets:
        raw_value = bucket.get("key", "")
        clean_value = sanitize_element(element=raw_value)
        if clean_value:
            results.add(clean_value)
    return results


def get_distinct_values(field_name, max_size=10000):
    """
    Generic function to get distinct values for a single field.

    Args:
        field_name (str): The field to get distinct values for
        max_size (int): Max terms to retrieve

    Returns:
        set: Distinct, sanitized values
    """
    aggs = req_aggs({field_name: max_size})
    buckets = aggs.get(field_name, {}).get("buckets", [])
    return parse_buckets(buckets)


def get_cty_org_src():
    """
    Get distinct values for country, organization, and source.

    Returns:
        tuple: (countries, organizations, sources) as sets
    """
    fields = {
        "country": MAX_LIST_COUNTRY,
        "organization": MAX_LIST_ORGANIZATION,
        "source": MAX_LIST_SOURCE,
    }

    aggs = req_aggs(fields)

    return (
        parse_buckets(aggs.get("country", {}).get("buckets", [])),
        parse_buckets(aggs.get("organization", {}).get("buckets", [])),
        parse_buckets(aggs.get("source", {}).get("buckets", []))
    )

def get_country_list():
    """Get all distinct countries from OpenSearch"""
    return get_distinct_values("country", max_size=MAX_LIST_COUNTRY)


def get_organization_list():
    """Get all distinct organizations from OpenSearch"""
    return get_distinct_values("organization", max_size=MAX_LIST_ORGANIZATION)

def get_source_list():
    """Get all distinct sources from OpenSearch"""
    return get_distinct_values("source", max_size=MAX_LIST_SOURCE)
