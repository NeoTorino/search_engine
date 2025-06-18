"""
Core Security Functions
Consolidates all main security validation and enforcement
"""
import re
import json
import hashlib
import logging
import unicodedata
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

import bleach
import redis
from flask import request, abort, g

from security.settings import security_settings

# Initialize logger
security_logger = logging.getLogger('security')

class SecurityCore:
    """Main security enforcement class"""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client or self._get_redis_client()
        self.logger = security_logger

    def _get_redis_client(self):
        """Get Redis client with error handling"""
        try:
            return redis.Redis.from_url(security_settings.get_redis_url())
        except Exception as e:
            self.logger.warning("Redis connection failed: %s", e)
            return None

    # === INPUT VALIDATION ===

    def validate_search_query(self, query: str) -> Tuple[bool, str]:
        """Validate search query with comprehensive security checks"""
        if not query:
            return True, ""

        # Length check
        if len(query) > security_settings.MAX_QUERY_LENGTH:
            return False, "Search query too long"

        # Check for dangerous patterns
        for pattern_type, patterns in security_settings.DANGEROUS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    self.log_security_event(
                        "DANGEROUS_PATTERN_DETECTED",
                        f"Pattern type: {pattern_type}, Query: {query[:50]}..."
                    )
                    return False, "Invalid characters in search query"

        # Check for excessive special characters
        special_char_count = len(re.findall(r'[^\w\s-]', query))
        if special_char_count > len(query) * 0.3:
            return False, "Too many special characters"

        return True, self.sanitize_input(query)

    def validate_filter_values(self, values: List[str], filter_type: str = 'default') -> List[str]:
        """Validate and sanitize filter values"""
        if not values:
            return []

        max_items = security_settings.MAX_FILTER_ITEMS.get(filter_type,
                                                          security_settings.MAX_FILTER_ITEMS['default'])

        if len(values) > max_items:
            values = values[:max_items]

        sanitized = []
        for value in values:
            clean_value = self.sanitize_input(value, max_length=100)
            if clean_value and len(clean_value) >= 2:
                if self._is_safe_filter_value(clean_value):
                    sanitized.append(clean_value)

        return sanitized

    def validate_pagination(self, offset: int, limit: int) -> Tuple[int, int, Optional[str]]:
        """Validate pagination parameters"""
        try:
            offset = int(offset) if offset else 0
            limit = int(limit) if limit else 20
        except (ValueError, TypeError):
            return 0, 20, "Invalid pagination parameters"

        if offset < 0:
            offset = 0
        elif offset > security_settings.MAX_PAGINATION_OFFSET:
            return offset, limit, f"Offset too large (max: {security_settings.MAX_PAGINATION_OFFSET})"

        if limit < 1:
            limit = 20
        elif limit > security_settings.MAX_PAGINATION_LIMIT:
            limit = security_settings.MAX_PAGINATION_LIMIT

        return offset, limit, None

    def sanitize_input(self, input_str: str, max_length: int = None, allow_html: bool = False) -> str:
        """Comprehensive input sanitization"""
        if not input_str or not isinstance(input_str, str):
            return ""

        max_length = max_length or security_settings.MAX_STRING_LENGTH

        # Remove null bytes and control characters
        input_str = input_str.replace('\x00', '')
        input_str = ''.join(char for char in input_str if ord(char) >= 32 or char in '\t\n\r')

        # Normalize unicode
        input_str = unicodedata.normalize('NFKC', input_str)

        # Length limiting
        input_str = input_str[:max_length]

        if allow_html:
            # Use bleach for HTML sanitization
            input_str = bleach.clean(
                input_str,
                tags=security_settings.ALLOWED_HTML_TAGS,
                attributes=security_settings.ALLOWED_HTML_ATTRIBUTES,
                strip=True
            )
        else:
            # Remove all HTML/XML tags
            input_str = re.sub(r'<[^>]*>', '', input_str)

        # Remove dangerous patterns
        for patterns in security_settings.DANGEROUS_PATTERNS.values():
            for pattern in patterns:
                input_str = re.sub(pattern, '', input_str, flags=re.IGNORECASE)

        return input_str.strip()

    def _is_safe_filter_value(self, value: str) -> bool:
        """Check if filter value is safe"""
        dangerous_patterns = [
            r'script\s*:', r'javascript:', r'eval\s*\(',
            r'\{.*\}', r'\[.*\]', r'<.*>', r';\s*\w+',
            r'\$\w+', r'#\w+', r'@\w+'
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return False

        return True

    # === REQUEST VALIDATION ===

    def validate_request_integrity(self, req) -> bool:
        """Advanced request validation"""
        # Check for request smuggling
        if req.headers.get('Transfer-Encoding') and req.headers.get('Content-Length'):
            self.logger.warning("Potential request smuggling attempt")
            return False

        # Check X-Forwarded-For chain
        xff = req.headers.get('X-Forwarded-For', '')
        if xff and len(xff.split(',')) > 5:
            self.logger.warning("Suspicious X-Forwarded-For chain")
            return False

        # Validate HTTP method
        if req.method not in security_settings.ALLOWED_HTTP_METHODS:
            self.logger.warning("Unusual HTTP method: %s", req.method)
            return False

        return True

    def detect_bot_behavior(self, req) -> bool:
        """Detect potential bot/scraper behavior"""
        user_agent = req.headers.get('User-Agent', '').lower()

        # Check bot patterns
        for pattern in security_settings.BOT_PATTERNS:
            if re.search(pattern, user_agent):
                return True

        # Check for missing Accept header
        if not req.headers.get('Accept'):
            return True

        # Check for too many parameters
        if req.args and len(req.args) > 20:
            return True

        return False

    def validate_json_request(self, data: Any) -> bool:
        """Validate JSON request data"""
        if not isinstance(data, (dict, list)):
            return True

        # Size check
        if len(str(data)) > security_settings.MAX_JSON_SIZE:
            return False

        # Structure check
        return not self._contains_dangerous_json_patterns(data)

    def _contains_dangerous_json_patterns(self, data: Any, max_depth: int = 10, current_depth: int = 0) -> bool:
        """Check for dangerous patterns in JSON data"""
        if current_depth > max_depth:
            return True

        if isinstance(data, dict):
            if len(data) > 100:
                return True
            for key, value in data.items():
                if isinstance(key, str) and any(
                    re.search(pattern, key, re.IGNORECASE)
                    for patterns in security_settings.DANGEROUS_PATTERNS.values()
                    for pattern in patterns
                ):
                    return True
                if self._contains_dangerous_json_patterns(value, max_depth, current_depth + 1):
                    return True
        elif isinstance(data, list):
            if len(data) > 1000:
                return True
            for item in data:
                if self._contains_dangerous_json_patterns(item, max_depth, current_depth + 1):
                    return True
        elif isinstance(data, str):
            if len(data) > 10000:
                return True
            # Check for dangerous patterns
            for patterns in security_settings.DANGEROUS_PATTERNS.values():
                for pattern in patterns:
                    if re.search(pattern, data, re.IGNORECASE):
                        return True

        return False

    # === IP AND ACCESS CONTROL ===

    def get_client_fingerprint(self, req) -> str:
        """Create unique client fingerprint"""
        components = [
            req.headers.get('User-Agent', ''),
            req.headers.get('Accept-Language', ''),
            req.headers.get('Accept-Encoding', ''),
            req.remote_addr or '',
        ]

        fingerprint_string = '|'.join(components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]

    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        if not self.redis_client:
            return False

        try:
            blocked_key = f"blocked_ip:{ip}"
            return self.redis_client.exists(blocked_key)
        except Exception as e:
            self.logger.warning("Redis error checking blocked IP: %s", e)
            return False

    def block_ip(self, ip: str, duration: int = None) -> None:
        """Block IP address"""
        if not self.redis_client:
            return

        duration = duration or security_settings.BLOCKED_IP_DURATION

        try:
            blocked_key = f"blocked_ip:{ip}"
            self.redis_client.setex(blocked_key, duration, "1")
            self.logger.warning("IP %s blocked for %s seconds", ip, duration)
        except Exception as e:
            self.logger.error("Failed to block IP %s: %s", ip, e)

    def increment_suspicious_activity(self, ip: str) -> bool:
        """Track suspicious activity and block if threshold exceeded"""
        if not self.redis_client:
            return False

        try:
            key = f"suspicious:{ip}:{datetime.utcnow().hour}"
            count = self.redis_client.incr(key)
            self.redis_client.expire(key, 3600)

            if count >= security_settings.SUSPICIOUS_REQUEST_THRESHOLD:
                self.block_ip(ip)
                return True
        except Exception as e:
            self.logger.error("Failed to track suspicious activity for %s: %s", ip, e)

        return False

    # === OPENSEARCH SECURITY ===

    def sanitize_opensearch_query(self, query_dict: Dict) -> Dict:
        """Sanitize OpenSearch query dictionary"""
        if not isinstance(query_dict, dict):
            return {}

        sanitized = {}
        for key, value in query_dict.items():
            clean_key = self._sanitize_opensearch_field_name(key)
            if not clean_key:
                continue

            if isinstance(value, str):
                clean_value = self._sanitize_opensearch_value(value)
            elif isinstance(value, dict):
                clean_value = self.sanitize_opensearch_query(value)
            elif isinstance(value, list):
                clean_value = [
                    self._sanitize_opensearch_value(v) if isinstance(v, str)
                    else self.sanitize_opensearch_query(v) if isinstance(v, dict)
                    else v for v in value if self._is_safe_opensearch_value(v)
                ]
            else:
                clean_value = value

            sanitized[clean_key] = clean_value

        return sanitized

    def _sanitize_opensearch_field_name(self, field_name: str) -> str:
        """Sanitize OpenSearch field names"""
        if not isinstance(field_name, str):
            return ""

        # Allow only safe characters
        if not re.match(r'^[a-zA-Z0-9._-]+$', field_name):
            return ""

        # Check against dangerous fields
        if field_name.startswith('_') and field_name not in ['_all']:
            if any(dangerous in field_name for dangerous in security_settings.DANGEROUS_OPENSEARCH_FIELDS):
                return ""

        return field_name

    def _sanitize_opensearch_value(self, value: str) -> str:
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

        # Remove JSON injection attempts
        clean_value = re.sub(r'\{[^}]*script[^}]*\}', '', clean_value, flags=re.IGNORECASE)
        clean_value = re.sub(r'\{[^}]*source[^}]*\}', '', clean_value, flags=re.IGNORECASE)

        return self.sanitize_input(clean_value, max_length=1000)

    def _is_safe_opensearch_value(self, value: Any) -> bool:
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

    # === LOGGING ===

    def log_security_event(self, event_type: str, details: str, severity: str = "WARNING", ip: str = None) -> None:
        """Log security events with structured format"""
        if ip is None and request:
            ip = request.remote_addr

        event_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'details': details,
            'severity': severity,
            'ip_address': ip,
            'user_agent': request.headers.get('User-Agent', '') if request else '',
            'endpoint': request.endpoint if request else '',
            'method': request.method if request else ''
        }

        # Log to file
        log_level = logging.ERROR if severity == "ERROR" else logging.WARNING
        self.logger.log(log_level, "SECURITY_EVENT: %s", json.dumps(event_data))

        # Store in Redis for monitoring
        if self.redis_client:
            try:
                self.redis_client.lpush('security_events', json.dumps(event_data))
                self.redis_client.ltrim('security_events', 0, security_settings.MAX_LOG_EVENTS_IN_REDIS - 1)
            except Exception as e:
                self.logger.warning("Failed to store security event in Redis: %s", e)

# Global instance
security_core = SecurityCore()

# === CONVENIENCE FUNCTIONS ===

def get_search_params() -> Dict[str, Any]:
    """Extract and validate search parameters from request"""
    try:
        # Validate search query
        raw_query = request.args.get('q', '')
        is_valid, sanitized_query = security_core.validate_search_query(raw_query)
        if not is_valid:
            sanitized_query = ''

        # Validate filters
        countries = security_core.validate_filter_values(
            request.args.getlist('country'), 'countries'
        )
        organizations = security_core.validate_filter_values(
            request.args.getlist('organization'), 'organizations'
        )
        sources = security_core.validate_filter_values(
            request.args.getlist('source'), 'sources'
        )

        # Validate date parameter
        date_posted_days = request.args.get('date_posted_days', type=int)
        if date_posted_days is not None:
            if date_posted_days < 0:
                date_posted_days = None
            elif date_posted_days >= 31:
                date_posted_days = 365
            elif date_posted_days > 365:
                date_posted_days = 365

        # Validate pagination
        offset = request.args.get('offset', request.args.get('from', 0), type=int)
        limit = request.args.get('limit', 20, type=int)
        offset, limit, error = security_core.validate_pagination(offset, limit)

        if error:
            security_core.log_security_event("INVALID_PAGINATION", error)

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
        security_core.log_security_event("SEARCH_PARAMS_ERROR", "Error: %s", e)
        return {
            'query': '',
            'countries': [],
            'organizations': [],
            'sources': [],
            'date_posted_days': None,
            'offset': 0,
            'limit': 20
        }

def validate_request_security() -> bool:
    """Comprehensive request security validation"""
    if not request:
        return True

    # Skip security for certain endpoints
    if request.endpoint in security_settings.SKIP_SECURITY_ENDPOINTS:
        return True

    client_ip = request.remote_addr

    # Check if IP is blocked
    if security_core.is_ip_blocked(client_ip):
        security_core.log_security_event("BLOCKED_IP_ACCESS", "IP: %s", client_ip)
        abort(403)

    # Validate request integrity
    if not security_core.validate_request_integrity(request):
        security_core.increment_suspicious_activity(client_ip)
        security_core.log_security_event("REQUEST_INTEGRITY_FAILURE", "IP: %s", client_ip)
        abort(400)

    # Check for bot behavior
    if security_core.detect_bot_behavior(request):
        # Check for attack tools in user agent
        user_agent = request.headers.get('User-Agent', '').lower()
        if any(tool in user_agent for tool in security_settings.ATTACK_TOOL_PATTERNS):
            security_core.block_ip(client_ip)
            security_core.log_security_event("ATTACK_TOOL_DETECTED", "UA: %s, IP: %s", user_agent, client_ip)
            abort(403)

        security_core.log_security_event("BOT_DETECTED", f"IP: {client_ip}")
        abort(429)

    # Validate Host header
    host = request.headers.get('Host', '')
    if host:
        host_without_port = host.split(':')[0]
        allowed_hosts = security_settings.get_allowed_hosts()
        if host_without_port not in allowed_hosts:
            security_core.increment_suspicious_activity(client_ip)
            security_core.log_security_event("INVALID_HOST_HEADER", "Host: %s, IP: %s", host, client_ip)
            abort(400)

    # Check for path traversal
    path_lower = request.path.lower()
    traversal_patterns = ['../', '..\\', '%2e%2e%2f', '%2e%2e%5c', '..%2f', '..%5c']
    if any(pattern in path_lower for pattern in traversal_patterns):
        security_core.block_ip(client_ip)
        security_core.log_security_event("PATH_TRAVERSAL_ATTEMPT", "Path: %s, IP: %s", request.path, client_ip)
        abort(403)

    # Store client info
    g.client_fingerprint = security_core.get_client_fingerprint(request)
    g.client_ip = client_ip

    return True
