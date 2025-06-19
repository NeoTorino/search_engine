import re
import logging
from datetime import datetime
from flask import request

from security.core.sanitizers import sanitize_input

# Configure security logger
security_logger = logging.getLogger('security')

def sanitize_opensearch_query(query_dict):
    """
    Sanitize OpenSearch query dictionary to prevent injection attacks
    """
    if not isinstance(query_dict, dict):
        return {}

    sanitized = {}

    for key, value in query_dict.items():
        # Sanitize keys
        clean_key = sanitize_opensearch_field_name(key)
        if not clean_key:
            continue

        # Sanitize values based on type
        if isinstance(value, str):
            clean_value = sanitize_opensearch_value(value)
        elif isinstance(value, dict):
            clean_value = sanitize_opensearch_query(value)
        elif isinstance(value, list):
            clean_value = [sanitize_opensearch_value(v) if isinstance(v, str)
                          else sanitize_opensearch_query(v) if isinstance(v, dict)
                          else v for v in value if _is_safe_opensearch_value(v)]
        else:
            clean_value = value

        sanitized[clean_key] = clean_value

    return sanitized

def sanitize_opensearch_field_name(field_name):
    """Sanitize OpenSearch field names"""
    if not isinstance(field_name, str):
        return ""

    # Allow only alphanumeric, dots, underscores, and hyphens
    if not re.match(r'^[a-zA-Z0-9._-]+$', field_name):
        return ""

    # Prevent access to system fields
    dangerous_fields = [
        '_source', '_id', '_type', '_index', '_score',
        '_script', '_inline', '_file', '_id'
    ]

    if field_name.startswith('_') and field_name not in ['_all']:
        return ""

    return field_name



def validate_opensearch_aggregation(agg_dict):
    """Validate OpenSearch aggregation queries"""
    if not isinstance(agg_dict, dict):
        return {}

    # List of safe aggregation types
    safe_agg_types = [
        'terms', 'date_histogram', 'histogram', 'range',
        'sum', 'avg', 'min', 'max', 'count', 'cardinality',
        'percentiles', 'stats', 'extended_stats'
    ]

    sanitized = {}
    for key, value in agg_dict.items():
        if isinstance(value, dict):
            # Check if this is an aggregation definition
            agg_type = None
            for agg in safe_agg_types:
                if agg in value:
                    agg_type = agg
                    break

            if agg_type:
                # Sanitize the aggregation
                sanitized[sanitize_input(key)] = {
                    agg_type: sanitize_opensearch_query(value[agg_type])
                }
                # Handle sub-aggregations
                if 'aggs' in value or 'aggregations' in value:
                    sub_aggs_key = 'aggs' if 'aggs' in value else 'aggregations'
                    sanitized[sanitize_input(key)][sub_aggs_key] = validate_opensearch_aggregation(value[sub_aggs_key])

    return sanitized

def validate_opensearch_search_params(search_params):
    """
    Comprehensive validation of OpenSearch search parameters

    Args:
        search_params (dict): Dictionary containing search parameters

    Returns:
        dict: Sanitized search parameters
    """
    if not isinstance(search_params, dict):
        return {}

    sanitized_params = {}

    # Validate and sanitize query
    if 'query' in search_params:
        sanitized_params['query'] = sanitize_opensearch_query(search_params['query'])

    # Validate and sanitize aggregations
    if 'aggs' in search_params or 'aggregations' in search_params:
        aggs_key = 'aggs' if 'aggs' in search_params else 'aggregations'
        sanitized_params[aggs_key] = validate_opensearch_aggregation(search_params[aggs_key])

    # Validate size parameter
    if 'size' in search_params:
        try:
            size = int(search_params['size'])
            sanitized_params['size'] = min(max(0, size), 10000)  # Limit to reasonable range
        except (ValueError, TypeError):
            sanitized_params['size'] = 20  # Default size

    # Validate from parameter
    if 'from' in search_params:
        try:
            from_param = int(search_params['from'])
            sanitized_params['from'] = min(max(0, from_param), 10000)  # Limit to reasonable range
        except (ValueError, TypeError):
            sanitized_params['from'] = 0  # Default from

    # Validate sort parameter
    if 'sort' in search_params:
        sanitized_params['sort'] = _sanitize_opensearch_sort(search_params['sort'])

    # Validate _source parameter
    if '_source' in search_params:
        sanitized_params['_source'] = _sanitize_opensearch_source(search_params['_source'])

    # Validate highlight parameter
    if 'highlight' in search_params:
        sanitized_params['highlight'] = _sanitize_opensearch_highlight(search_params['highlight'])

    # Copy other safe parameters
    safe_params = ['timeout', 'terminate_after', 'track_total_hits']
    for param in safe_params:
        if param in search_params:
            sanitized_params[param] = search_params[param]

    return sanitized_params

def _sanitize_opensearch_sort(sort_param):
    """Sanitize OpenSearch sort parameter"""
    if isinstance(sort_param, list):
        sanitized_sort = []
        for sort_item in sort_param:
            if isinstance(sort_item, dict):
                sanitized_item = {}
                for field, order_info in sort_item.items():
                    clean_field = sanitize_opensearch_field_name(field)
                    if clean_field:
                        if isinstance(order_info, str) and order_info.lower() in ['asc', 'desc']:
                            sanitized_item[clean_field] = order_info.lower()
                        elif isinstance(order_info, dict):
                            sanitized_order = {}
                            if 'order' in order_info and order_info['order'].lower() in ['asc', 'desc']:
                                sanitized_order['order'] = order_info['order'].lower()
                            sanitized_item[clean_field] = sanitized_order
                if sanitized_item:
                    sanitized_sort.append(sanitized_item)
            elif isinstance(sort_item, str):
                clean_field = sanitize_opensearch_field_name(sort_item)
                if clean_field:
                    sanitized_sort.append(clean_field)
        return sanitized_sort
    elif isinstance(sort_param, dict):
        return _sanitize_opensearch_sort([sort_param])
    elif isinstance(sort_param, str):
        clean_field = sanitize_opensearch_field_name(sort_param)
        return [clean_field] if clean_field else []

    return []

def _sanitize_opensearch_source(source_param):
    """Sanitize OpenSearch _source parameter"""
    if isinstance(source_param, list):
        sanitized_fields = []
        for field in source_param:
            if isinstance(field, str):
                clean_field = sanitize_opensearch_field_name(field)
                if clean_field:
                    sanitized_fields.append(clean_field)
        return sanitized_fields
    elif isinstance(source_param, str):
        clean_field = sanitize_opensearch_field_name(source_param)
        return [clean_field] if clean_field else []
    elif isinstance(source_param, bool):
        return source_param

    return True  # Default to include all fields

def _sanitize_opensearch_highlight(highlight_param):
    """Sanitize OpenSearch highlight parameter"""
    if not isinstance(highlight_param, dict):
        return {}

    sanitized_highlight = {}

    # Sanitize fields
    if 'fields' in highlight_param and isinstance(highlight_param['fields'], dict):
        sanitized_fields = {}
        for field, config in highlight_param['fields'].items():
            clean_field = sanitize_opensearch_field_name(field)
            if clean_field:
                if isinstance(config, dict):
                    # Allow only safe highlight configuration options
                    safe_config = {}
                    safe_options = ['fragment_size', 'number_of_fragments', 'type', 'pre_tags', 'post_tags']
                    for option in safe_options:
                        if option in config:
                            if option in ['pre_tags', 'post_tags'] and isinstance(config[option], list):
                                # Sanitize HTML tags
                                safe_config[option] = [str(tag)[:50] for tag in config[option][:5]]  # Limit tags
                            elif option in ['fragment_size', 'number_of_fragments']:
                                try:
                                    val = int(config[option])
                                    safe_config[option] = min(max(1, val), 1000)  # Reasonable limits
                                except (ValueError, TypeError):
                                    pass
                            elif option == 'type' and isinstance(config[option], str):
                                if config[option].lower() in ['unified', 'plain', 'fvh']:
                                    safe_config[option] = config[option].lower()
                    sanitized_fields[clean_field] = safe_config
                else:
                    sanitized_fields[clean_field] = {}
        sanitized_highlight['fields'] = sanitized_fields

    # Copy other safe highlight options
    safe_highlight_options = ['pre_tags', 'post_tags', 'fragment_size', 'number_of_fragments']
    for option in safe_highlight_options:
        if option in highlight_param:
            if option in ['pre_tags', 'post_tags'] and isinstance(highlight_param[option], list):
                sanitized_highlight[option] = [str(tag)[:50] for tag in highlight_param[option][:5]]
            elif option in ['fragment_size', 'number_of_fragments']:
                try:
                    val = int(highlight_param[option])
                    sanitized_highlight[option] = min(max(1, val), 1000)
                except (ValueError, TypeError):
                    pass

    return sanitized_highlight

def log_opensearch_security_event(event_type, details, severity="WARNING", query=None):
    """
    Log OpenSearch-specific security events

    Args:
        event_type (str): Type of security event
        details (str): Event details
        severity (str): Event severity level
        query (dict): OpenSearch query that triggered the event
    """
    event_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': f"OPENSEARCH_{event_type}",
        'details': details,
        'severity': severity,
        'ip_address': request.remote_addr if request else None,
        'user_agent': request.headers.get('User-Agent', '') if request else '',
        'endpoint': request.endpoint if request else '',
        'method': request.method if request else '',
        'query_snippet': str(query)[:500] if query else None  # Log first 500 chars of query
    }

    security_logger.log(
        logging.ERROR if severity == "ERROR" else logging.WARNING,
        "OPENSEARCH_SECURITY_EVENT: %s", str(event_data)
    )

def detect_opensearch_injection_attempt(query_dict):
    """
    Detect potential OpenSearch injection attempts

    Args:
        query_dict (dict): OpenSearch query dictionary

    Returns:
        tuple: (is_malicious, risk_level, details)
    """
    if not isinstance(query_dict, dict):
        return False, "LOW", "Invalid query format"

    risk_indicators = []
    risk_level = "LOW"

    # Convert to string for pattern matching
    query_str = str(query_dict).lower()

    # High-risk patterns
    high_risk_patterns = [
        r'script\s*:\s*{',
        r'inline\s*:\s*["\']',
        r'source\s*:\s*["\']',
        r'painless',
        r'groovy',
        r'_delete_by_query',
        r'_update_by_query',
        r'_bulk',
        r'system\s*\(',
        r'runtime\.exec'
    ]

    # Medium-risk patterns
    medium_risk_patterns = [
        r'script\s*:',
        r'params\s*:',
        r'lang\s*:',
        r'_source\s*:.*script',
        r'highlight.*script',
        r'sort.*script'
    ]

    # Check for high-risk patterns
    for pattern in high_risk_patterns:
        if re.search(pattern, query_str, re.IGNORECASE):
            risk_indicators.append(f"High-risk pattern: {pattern}")
            risk_level = "HIGH"

    # Check for medium-risk patterns if not already high risk
    if risk_level != "HIGH":
        for pattern in medium_risk_patterns:
            if re.search(pattern, query_str, re.IGNORECASE):
                risk_indicators.append(f"Medium-risk pattern: {pattern}")
                risk_level = "MEDIUM"

    # Check for excessive nesting (potential DoS)
    nesting_level = _calculate_nesting_level(query_dict)
    if nesting_level > 10:
        risk_indicators.append(f"Excessive nesting: {nesting_level} levels")
        risk_level = "HIGH" if nesting_level > 20 else "MEDIUM"

    # Check for excessive query size
    query_size = len(str(query_dict))
    if query_size > 50000:  # 50KB
        risk_indicators.append(f"Large query size: {query_size} bytes")
        risk_level = "HIGH" if query_size > 100000 else "MEDIUM"

    is_malicious = len(risk_indicators) > 0
    details = "; ".join(risk_indicators) if risk_indicators else "No suspicious patterns detected"

    return is_malicious, risk_level, details

def _calculate_nesting_level(obj, current_level=0):
    """Calculate the maximum nesting level of a dictionary or list"""
    if current_level > 50:  # Prevent infinite recursion
        return current_level

    max_level = current_level

    if isinstance(obj, dict):
        for value in obj.values():
            level = _calculate_nesting_level(value, current_level + 1)
            max_level = max(max_level, level)
    elif isinstance(obj, list):
        for item in obj:
            level = _calculate_nesting_level(item, current_level + 1)
            max_level = max(max_level, level)

    return max_level