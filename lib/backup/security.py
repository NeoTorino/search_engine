import re
import unicodedata
import json
import logging
from functools import wraps
from datetime import datetime
import bleach
from flask import request, abort, current_app

from security_config import SecurityConfig

# Configure security logger
security_logger = logging.getLogger('security')

def validate_request_size(max_size=1024*1024):  # 1MB default
    """Validate request size to prevent DoS"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.content_length and request.content_length > max_size:
                log_security_event("LARGE_REQUEST", f"Size: {request.content_length}")
                abort(413)  # Request Entity Too Large
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_json_request(f):
    """Validate JSON requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.is_json:
            try:
                # Limit JSON depth and size
                data = request.get_json(force=True)
                if isinstance(data, dict) and len(str(data)) > 10000:
                    log_security_event("LARGE_JSON", "JSON too large")
                    abort(400)

                # Check for dangerous JSON structures
                if _contains_dangerous_json_patterns(data):
                    log_security_event("MALICIOUS_JSON", "Dangerous JSON pattern detected")
                    abort(400)

            except Exception as e:
                log_security_event("INVALID_JSON", str(e))
                abort(400)
        return f(*args, **kwargs)
    return decorated_function

def _contains_dangerous_json_patterns(data, max_depth=10, current_depth=0):
    """Check for dangerous patterns in JSON data"""
    if current_depth > max_depth:
        return True

    if isinstance(data, dict):
        if len(data) > 100:  # Prevent excessive keys
            return True
        for key, value in data.items():
            if isinstance(key, str) and _is_dangerous_string(key):
                return True
            if _contains_dangerous_json_patterns(value, max_depth, current_depth + 1):
                return True
    elif isinstance(data, list):
        if len(data) > 1000:  # Prevent excessive array size
            return True
        for item in data:
            if _contains_dangerous_json_patterns(item, max_depth, current_depth + 1):
                return True
    elif isinstance(data, str):
        if len(data) > 10000 or _is_dangerous_string(data):
            return True

    return False

def _is_dangerous_string(text):
    """Check if string contains dangerous patterns"""
    dangerous_patterns = [
        r'javascript:', r'vbscript:', r'data:', r'file:', r'ftp:',
        r'<script', r'</script', r'eval\s*\(', r'setTimeout\s*\(',
        r'setInterval\s*\(', r'Function\s*\(', r'constructor\s*\(',
        r'__proto__', r'prototype\.', r'\.constructor'
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def sanitize_input(input_str, max_length=200, allow_basic_html=False):
    """
    Comprehensive input sanitization with security focus
    """
    if not input_str or not isinstance(input_str, str):
        return ""

    # Remove null bytes and control characters
    input_str = input_str.replace('\x00', '')
    input_str = ''.join(char for char in input_str if ord(char) >= 32 or char in '\t\n\r')

    # Normalize unicode to prevent bypass attempts
    input_str = unicodedata.normalize('NFKC', input_str)

    # Length limiting
    input_str = input_str[:max_length]

    if allow_basic_html:
        # Use bleach for HTML sanitization
        allowed_tags = ['b', 'i', 'em', 'strong']
        allowed_attributes = {}
        input_str = bleach.clean(input_str, tags=allowed_tags, attributes=allowed_attributes, strip=True)
    else:
        # Remove all HTML/XML tags
        input_str = re.sub(r'<[^>]*>', '', input_str)

    # Remove dangerous characters for injection attacks
    dangerous_chars = ['<', '>', '"', "'", '`', '\\', ';', '(', ')', '{', '}', '[', ']', '$', '|']
    for char in dangerous_chars:
        input_str = input_str.replace(char, '')

    # Remove script-related keywords (case insensitive)
    script_patterns = [
        r'javascript:', r'vbscript:', r'data:', r'file:', r'ftp:',
        r'on\w+\s*=', r'script', r'iframe', r'object', r'embed',
        r'expression\s*\(', r'url\s*\(', r'import\s+', r'@import',
        r'eval\s*\(', r'exec\s*\(', r'system\s*\('
    ]

    for pattern in script_patterns:
        input_str = re.sub(pattern, '', input_str, flags=re.IGNORECASE)

    # Trim whitespace
    input_str = input_str.strip()

    return input_str

def validate_search_query(query):
    """
    Validate search query with comprehensive security checks
    """
    if not query:
        return True, ""

    # Check for excessively long queries
    if len(query) > 200:
        return False, "Search query too long"

    # Check for suspicious patterns (SQL, NoSQL, OpenSearch injection)
    suspicious_patterns = [
        # SQL injection patterns
        r'union\s+select', r'drop\s+table', r'delete\s+from',
        r'insert\s+into', r'update\s+set', r'exec\s*\(',

        # Script injection
        r'<script', r'javascript:', r'vbscript:',

        # OpenSearch/Elasticsearch specific patterns
        r'_search\s*\{', r'_bulk\s*\{', r'_delete_by_query',
        r'_update_by_query', r'script\s*:', r'inline\s*:',
        r'source\s*:', r'params\s*:', r'lang\s*:',

        # JSON injection patterns
        r'\{.*script.*\}', r'\{.*source.*\}', r'\{.*inline.*\}',

        # Command injection
        r';\s*\w+', r'\|\s*\w+', r'&&\s*\w+', r'\$\(', r'`.*`',

        # Path traversal
        r'\.\./', r'\.\.\\', r'/etc/', r'/proc/', r'/sys/',

        # LDAP injection
        r'\(\s*\|', r'\(\s*&', r'\*\s*\)', r'=\s*\*'
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return False, "Invalid characters in search query"

    # Check for excessive special characters (potential obfuscation)
    special_char_count = len(re.findall(r'[^\w\s-]', query))
    if special_char_count > len(query) * 0.3:  # More than 30% special chars
        return False, "Too many special characters"

    return True, sanitize_input(query)

def validate_filter_values(values, allowed_values=None, max_items=50):
    """
    Validate filter values with security checks
    """
    if not values:
        return []

    if len(values) > max_items:
        values = values[:max_items]

    sanitized = []
    for value in values:
        clean_value = sanitize_input(value, max_length=100)
        if clean_value and len(clean_value) >= 2:  # Minimum length check
            # Additional security check for filter values
            if _is_safe_filter_value(clean_value):
                if allowed_values is None or clean_value in allowed_values:
                    sanitized.append(clean_value)

    return sanitized

def _is_safe_filter_value(value):
    """Check if filter value is safe"""
    # Reject values that look like injection attempts
    dangerous_patterns = [
        r'script\s*:', r'javascript:', r'eval\s*\(',
        r'\{.*\}', r'\[.*\]', r'<.*>', r';\s*\w+',
        r'\$\w+', r'#\w+', r'@\w+'
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            return False

    return True

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

def sanitize_opensearch_value(value):
    """Sanitize OpenSearch query values"""
    if not isinstance(value, str):
        return value

    # Remove script-related content
    script_patterns = [
        r'script\s*:', r'inline\s*:', r'source\s*:',
        r'params\s*:', r'lang\s*:', r'file\s*:',
        r'painless', r'groovy', r'expression'
    ]

    clean_value = value
    for pattern in script_patterns:
        clean_value = re.sub(pattern, '', clean_value, flags=re.IGNORECASE)

    # Remove potential JSON injection
    clean_value = re.sub(r'\{[^}]*script[^}]*\}', '', clean_value, flags=re.IGNORECASE)
    clean_value = re.sub(r'\{[^}]*source[^}]*\}', '', clean_value, flags=re.IGNORECASE)

    return sanitize_input(clean_value, max_length=1000)

def _is_safe_opensearch_value(value):
    """Check if value is safe for OpenSearch"""
    if isinstance(value, str):
        dangerous_patterns = [
            r'script\s*:', r'inline\s*:', r'source\s*:',
            r'_delete', r'_update', r'_bulk'
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return False

    return True

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

def log_security_event(event_type, details, severity="WARNING", ip_address=None):
    """
    Log security events with structured format
    """
    if ip_address is None and request:
        ip_address = request.remote_addr

    event_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'details': details,
        'severity': severity,
        'ip_address': ip_address,
        'user_agent': request.headers.get('User-Agent', '') if request else '',
        'endpoint': request.endpoint if request else '',
        'method': request.method if request else ''
    }

    security_logger.log(
        logging.ERROR if severity == "ERROR" else logging.WARNING,
        "SECURITY_EVENT: %s", json.dumps(event_data)
    )

def validate_pagination_params(offset, limit, max_limit=100, max_offset=10000):
    """
    Validate pagination parameters to prevent resource exhaustion
    """
    try:
        offset = int(offset) if offset else 0
        limit = int(limit) if limit else 20
    except (ValueError, TypeError):
        return 0, 20, "Invalid pagination parameters"

    if offset < 0:
        offset = 0
    elif offset > max_offset:
        return offset, limit, f"Offset too large (max: {max_offset})"

    if limit < 1:
        limit = 20
    elif limit > max_limit:
        limit = max_limit

    return offset, limit, None

def validate_date_range(start_date, end_date, max_range_days=365):
    """
    Validate date range parameters
    """
    try:
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None, None, "Invalid date format"

    if start_date and end_date:
        if start_date > end_date:
            return None, None, "Start date must be before end date"

        date_diff = (end_date - start_date).days
        if date_diff > max_range_days:
            return None, None, f"Date range too large (max: {max_range_days} days)"

    return start_date, end_date, None

def rate_limit_key_func():
    """Generate rate limiting key based on IP and user agent"""
    if not request:
        return "unknown"

    ip = request.remote_addr or "unknown"
    user_agent_hash = hash(request.headers.get('User-Agent', ''))
    return f"{ip}:{user_agent_hash}"

def detect_bot_behavior():
    """Detect potential bot/scraper behavior"""
    if not request:
        return False

    user_agent = request.headers.get('User-Agent', '').lower()

    # Common bot patterns
    bot_patterns = [
        r'bot', r'crawl', r'spider', r'scrape', r'fetch',
        r'curl', r'wget', r'python', r'java', r'go-http',
        r'automated', r'scanner', r'monitor'
    ]

    for pattern in bot_patterns:
        if re.search(pattern, user_agent):
            return True

    # Check for missing common headers
    if not request.headers.get('Accept'):
        return True

    # Check for suspicious request patterns
    if request.args and len(request.args) > 20:  # Too many parameters
        return True

    return False

def sanitize_filename(filename):
    """Sanitize filename for safe file operations"""
    if not filename:
        return ""

    # Remove path traversal attempts
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')

    # Keep only safe characters
    filename = re.sub(r'[^\w\-_\.]', '', filename)

    # Limit length
    filename = filename[:100]

    return filename

def validate_content_type(allowed_types):
    """Validate request content type"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            content_type = request.content_type
            if content_type and not any(ct in content_type for ct in allowed_types):
                log_security_event("INVALID_CONTENT_TYPE", f"Content-Type: {content_type}")
                abort(415)  # Unsupported Media Type
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_search_params(max_countries=20, max_organizations=50, max_sources=10, max_limit=100, max_offset=1000):
    """
    Extract and return standardized search parameters from request with comprehensive security validation

    Args:
        max_countries (int): Maximum number of country filters allowed
        max_organizations (int): Maximum number of organization filters allowed
        max_sources (int): Maximum number of source filters allowed
        max_limit (int): Maximum pagination limit allowed
        max_offset (int): Maximum pagination offset allowed

    Returns:
        dict: Sanitized and validated search parameters
    """
    try:
        # Validate search query
        raw_query = request.args.get('q', '')
        is_valid, sanitized_query = validate_search_query(raw_query)
        if not is_valid:
            security_logger.warning("Invalid search query blocked: %s", raw_query)
            log_security_event("INVALID_SEARCH_QUERY", f"Blocked query: {raw_query}")
            sanitized_query = ''

        # Validate filter parameters with configurable limits
        countries = validate_filter_values(
            request.args.getlist('country'), 
            max_items=max_countries
        )

        organizations = validate_filter_values(
            request.args.getlist('organization'), 
            max_items=max_organizations
        )

        sources = validate_filter_values(
            request.args.getlist('source'), 
            max_items=max_sources
        )

        # Validate date parameter with special handling for >= 31 days
        date_posted_days = request.args.get('date_posted_days', type=int)
        if date_posted_days is not None:
            # Limit date range to reasonable values
            if date_posted_days < 0:
                log_security_event("INVALID_DATE_RANGE", f"Negative date days: {date_posted_days}")
                date_posted_days = None
            elif date_posted_days >= 31:
                # If >= 31 days, treat as "everything" (365 days)
                date_posted_days = 365
            elif date_posted_days > 365:
                log_security_event("INVALID_DATE_RANGE", f"Date days too large: {date_posted_days}")
                date_posted_days = 365

        # Validate pagination parameters - support both 'offset'/'from' and 'limit' parameters
        offset = request.args.get('offset', request.args.get('from', 0), type=int)
        limit = request.args.get('limit', 20, type=int)
        offset, limit, error = validate_pagination_params(offset, limit, max_limit=max_limit, max_offset=max_offset)
        if error:
            log_security_event("INVALID_PAGINATION", error)

        return {
            'query': sanitized_query,
            'countries': countries,
            'organizations': organizations,
            'sources': sources,
            'date_posted_days': date_posted_days,
            'offset': offset,
            'limit': limit
        }

    except Exception as e:
        security_logger.error("Error processing search parameters: %s", e)
        log_security_event("SEARCH_PARAMS_ERROR", f"Error: {e}")
        # Return safe defaults
        return {
            'query': '',
            'countries': [],
            'organizations': [],
            'sources': [],
            'date_posted_days': None,
            'offset': 0,
            'limit': 20
        }

def get_limiter():
    """Get limiter from extensions safely"""
    try:
        from app_factory.extensions import get_extensions
        extensions = get_extensions()
        return extensions.get('limiter')
    except Exception as e:
        current_app.logger.error(f"Failed to get limiter: {e}")
        return None

def security_check():
    """Comprehensive security check decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for bot behavior
            if detect_bot_behavior():
                log_security_event("BOT_DETECTED", "Suspicious bot behavior detected")
                abort(429)  # Too Many Requests

            # Validate request size
            if request.content_length and request.content_length > 1024*10:  # 10KB limit for API
                log_security_event("LARGE_REQUEST", f"Size: {request.content_length}")
                abort(413)  # Request Entity Too Large

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit_decorator(rate_limit_key):
    """Dynamic rate limiter decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            limiter = get_limiter()
            if limiter:
                # Apply rate limiting
                try:
                    rate_limit = SecurityConfig.RATE_LIMITS['api'][2]
                    # Use limiter's test method to check if request should be limited
                    limiter.test(rate_limit)
                except Exception as e:
                    current_app.logger.warning(f"Rate limiting failed: {e}")
                    # Continue without rate limiting if it fails

            return f(*args, **kwargs)
        return decorated_function
    return decorator