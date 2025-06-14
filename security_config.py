import os
import re
import hashlib
import logging
from datetime import datetime
from functools import wraps
import redis

from flask import request, abort, g

class SecurityConfig:
    """Centralized security configuration"""

    # Rate limiting tiers
    RATE_LIMITS = {
        'default': ["2000 per day", "200 per hour", "20 per minute"],
        'search': ["1000 per day", "100 per hour", "10 per minute"],
        'api': ["500 per day", "50 per hour", "5 per minute"],
        'auth': ["10 per hour", "3 per minute"],  # For future auth endpoints
    }

    # Input validation limits
    MAX_QUERY_LENGTH = 200
    MAX_FILTER_ITEMS = 10
    MAX_REQUEST_SIZE = 1024 * 1024  # 1MB
    MAX_JSON_SIZE = 10000
    MAX_PAGINATION_OFFSET = 10000
    MAX_DATE_RANGE_DAYS = 365

    # Security monitoring thresholds
    SUSPICIOUS_REQUEST_THRESHOLD = 50  # per hour
    BLOCKED_IP_DURATION = 3600  # 1 hour

    # Allowed file extensions (if you plan to add file uploads)
    ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.doc', '.docx'}

    # Sensitive endpoints that need extra protection
    SENSITIVE_ENDPOINTS = {
        'api.security_stats',
        'main.stats',
        'admin',  # Future admin endpoints
    }

class SecurityEnforcer:
    """Advanced security enforcement"""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client or redis.Redis.from_url(
            os.getenv('REDIS_URL', 'redis://localhost:6379')
        )
        self.logger = logging.getLogger('security')

        # Validate Redis connection at startup
        if not self.validate_redis_connection():
            self.logger.error("Redis connection validation failed - security features may be degraded")

    def get_client_fingerprint(self, req):
        """Create a unique fingerprint for the client"""
        components = [
            req.headers.get('User-Agent', ''),
            req.headers.get('Accept-Language', ''),
            req.headers.get('Accept-Encoding', ''),
            req.remote_addr or '',
        ]

        fingerprint_string = '|'.join(components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]

    def is_ip_blocked(self, ip):
        """Check if IP is temporarily blocked"""
        blocked_key = f"blocked_ip:{ip}"
        return self.redis_client.exists(blocked_key)

    def block_ip(self, ip, duration=None):
        """Temporarily block an IP address"""
        if duration is None:
            duration = SecurityConfig.BLOCKED_IP_DURATION

        blocked_key = f"blocked_ip:{ip}"
        self.redis_client.setex(blocked_key, duration, "1")
        self.logger.warning("IP %s blocked for %s seconds", ip, duration)

    def increment_suspicious_activity(self, ip):
        """Track suspicious activity and block if threshold exceeded"""
        key = f"suspicious:{ip}:{datetime.utcnow().hour}"
        count = self.redis_client.incr(key)
        self.redis_client.expire(key, 3600)  # Expire after 1 hour

        if count >= SecurityConfig.SUSPICIOUS_REQUEST_THRESHOLD:
            self.block_ip(ip)
            return True
        return False

    def validate_request_integrity(self, req):
        """Advanced request validation"""
        # Check for request smuggling attempts
        if req.headers.get('Transfer-Encoding') and req.headers.get('Content-Length'):
            self.logger.warning("Potential request smuggling attempt")
            return False

        # Check for suspicious header combinations
        if req.headers.get('X-Forwarded-For') and len(req.headers.get('X-Forwarded-For', '').split(',')) > 5:
            self.logger.warning("Suspicious X-Forwarded-For chain")
            return False

        # Validate HTTP method
        if req.method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
            self.logger.warning("Unusual HTTP method: %s", req.method)
            return False

        return True

    def validate_redis_connection(self):
        """Validate Redis connection and configuration"""
        try:
            # Test connection
            self.redis_client.ping()
            
            # Check if AUTH is configured (for production)
            if os.getenv('FLASK_ENV') == 'production':
                redis_url = os.getenv('REDIS_URL', '')
                if not ('password' in redis_url or '@' in redis_url):
                    self.logger.warning("Redis authentication not configured in production")
            
            return True
        except Exception as e:
            self.logger.error("Redis connection failed: %s", e)
            return False

def create_security_middleware(app, security_enforcer):
    """Create comprehensive security middleware"""

    @app.before_request
    def comprehensive_security_check():
        """Enhanced security checks"""
        client_ip = request.remote_addr

        # Skip security checks for health endpoint
        if request.endpoint == 'main.health_check':
            return

        # Check if IP is blocked
        if security_enforcer.is_ip_blocked(client_ip):
            log_security_event("BLOCKED_IP_ACCESS", f"IP: {client_ip}")
            abort(403)

        # Validate request integrity
        if not security_enforcer.validate_request_integrity(request):
            security_enforcer.increment_suspicious_activity(client_ip)
            log_security_event("REQUEST_INTEGRITY_FAILURE", f"IP: {client_ip}")
            abort(400)

        # Enhanced User-Agent validation
        user_agent = request.headers.get('User-Agent', '')
        if not user_agent:
            log_security_event("NO_USER_AGENT", f"IP: {client_ip}")
            abort(400)

        # Block common attack tools
        suspicious_ua_patterns = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'zap', 'burp',
            'dirbuster', 'gobuster', 'wfuzz', 'ffuf', 'hydra'
        ]

        ua_lower = user_agent.lower()
        if any(pattern in ua_lower for pattern in suspicious_ua_patterns):
            # Log but don't immediately block - attackers can change UA easily
            security_enforcer.increment_suspicious_activity(client_ip)
            log_security_event("SUSPICIOUS_USER_AGENT", f"UA: {user_agent}, IP: {client_ip}", "WARNING")
            # Only block if they're also doing other suspicious things

        # Validate Host header more strictly (with port handling)
        host = request.headers.get('Host', '')
        allowed_hosts = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

        # Strip port from host for comparison
        host_without_port = host.split(':')[0] if host else ''

        if host and host_without_port not in allowed_hosts:
            security_enforcer.increment_suspicious_activity(client_ip)
            log_security_event("INVALID_HOST_HEADER", f"Host: {host}, IP: {client_ip}")
            abort(400)

        # Check for path traversal attempts (including encoded variants)
        path_lower = request.path.lower()
        traversal_patterns = ['../', '..\\', '%2e%2e%2f', '%2e%2e%5c', '..%2f', '..%5c', '%2e%2e/', '%2e%2e\\']
        if any(pattern in path_lower for pattern in traversal_patterns):
            security_enforcer.block_ip(client_ip)
            log_security_event("PATH_TRAVERSAL_ATTEMPT", f"Path: {request.path}, IP: {client_ip}")
            abort(403)

        # Store client fingerprint for tracking
        g.client_fingerprint = security_enforcer.get_client_fingerprint(request)
        g.client_ip = client_ip

def enhanced_input_validation():
    """Enhanced input validation decorators"""

    def validate_search_request(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Validate search query
            query = request.args.get('q', '')
            if len(query) > SecurityConfig.MAX_QUERY_LENGTH:
                log_security_event("QUERY_TOO_LONG", f"Length: {len(query)}")
                abort(400)

            # Validate pagination
            try:
                offset = int(request.args.get('from', 0))
                if offset > SecurityConfig.MAX_PAGINATION_OFFSET:
                    log_security_event("EXCESSIVE_PAGINATION", f"Offset: {offset}")
                    abort(400)
            except ValueError:
                abort(400)

            # Validate filter counts
            filter_counts = {
                'country': len(request.args.getlist('country')),
                'organization': len(request.args.getlist('organization')),
                'source': len(request.args.getlist('source'))
            }

            for filter_type, count in filter_counts.items():
                if count > SecurityConfig.MAX_FILTER_ITEMS:
                    log_security_event("EXCESSIVE_FILTERS", f"Type: {filter_type}, Count: {count}")
                    abort(400)

            return f(*args, **kwargs)
        return decorated_function

    def validate_api_request(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Additional API-specific validations
            if request.is_json:
                try:
                    data = request.get_json()
                    if data and len(str(data)) > SecurityConfig.MAX_JSON_SIZE:
                        log_security_event("JSON_TOO_LARGE", f"Size: {len(str(data))}")
                        abort(400)
                except Exception as e:
                    log_security_event("INVALID_JSON", str(e))
                    abort(400)

            return f(*args, **kwargs)
        return decorated_function

    return validate_search_request, validate_api_request

def setup_enhanced_logging():
    """Setup comprehensive security logging"""

    # Create logs directory
    os.makedirs('logs', exist_ok=True)

    # Configure security logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)

    # File handler for security events
    security_handler = logging.FileHandler('logs/security.log')
    security_handler.setLevel(logging.INFO)

    # Console handler for immediate alerts
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    security_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    security_logger.addHandler(security_handler)
    security_logger.addHandler(console_handler)

    return security_logger

def log_security_event(event_type, details, severity="INFO", ip=None):
    """Enhanced security event logging"""
    logger = logging.getLogger('security')

    if ip is None:
        ip = getattr(g, 'client_ip', 'unknown')

    fingerprint = getattr(g, 'client_fingerprint', 'unknown')

    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'severity': severity,
        'ip': ip,
        'fingerprint': fingerprint,
        'details': details,
        'user_agent': request.headers.get('User-Agent', '') if request else '',
        'path': request.path if request else '',
        'method': request.method if request else ''
    }

    log_message = f"[{severity}] {event_type}: {details} | IP: {ip} | Path: {request.path if request else 'N/A'}"

    if severity == "ERROR":
        logger.error(log_message)
    elif severity == "WARNING":
        logger.warning(log_message)
    else:
        logger.info(log_message)

    # Store in Redis for real-time monitoring (optional)
    try:
        redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        redis_client.lpush('security_events', str(log_entry))
        redis_client.ltrim('security_events', 0, 999)  # Keep last 1000 events
    except (redis.RedisError, ConnectionError) as e:
        logger.warning("Redis unavailable for security event storage: %s", e)

# Database security helpers
class DatabaseSecurity:
    """Database security utilities"""

    @staticmethod
    def escape_opensearch_query(query):
        """Escape special characters in OpenSearch queries"""
        special_chars = ['\\', '+', '-', '=', '&', '|', '>', '<', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?', ':', '/']

        for char in special_chars:
            query = query.replace(char, f'\\{char}')

        return query

    @staticmethod
    def validate_opensearch_query(query):
        """Validate OpenSearch query for safety"""
        if not query or not isinstance(query, str):
            return False, "Invalid query type"

        # Check for script injection attempts
        dangerous_patterns = [
            'script', 'eval', 'function', 'process', 'require',
            'import', 'exec', 'system', 'cmd', 'shell'
        ]

        query_lower = query.lower()
        for pattern in dangerous_patterns:
            if pattern in query_lower:
                return False, f"Dangerous pattern detected: {pattern}"

        # Check query length
        if len(query) > 1000:
            return False, "Query too long"

        return True, "Valid"

    @staticmethod
    def sanitize_sort_field(field):
        """Sanitize sort field names"""
        # Only allow alphanumeric characters, dots, and underscores
        if not re.match(r'^[a-zA-Z0-9._]+$', field):
            return None

        # Whitelist allowed sort fields
        allowed_fields = [
            'date_posted', 'title', 'organization', 'country',
            'source', 'created_at', 'updated_at', '_score'
        ]

        if field not in allowed_fields:
            return None

        return field