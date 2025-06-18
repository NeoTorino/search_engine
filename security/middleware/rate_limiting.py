"""
Rate limiting middleware for API endpoints
Reads configuration from settings.py and provides simple rate limiting functionality
"""

import time
import logging
from collections import defaultdict, deque
from threading import Lock
from functools import wraps
from flask import request, g
from security.settings import security_settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self):
        self.requests = defaultdict(deque)
        self.lock = Lock()
        self.blocked_ips = {}

    def is_allowed(self, key, limit, window):
        """Check if request is allowed based on rate limit"""
        current_time = time.time()

        with self.lock:
            # Clean old requests outside the window
            request_times = self.requests[key]
            while request_times and request_times[0] <= current_time - window:
                request_times.popleft()

            # Check if limit exceeded
            if len(request_times) >= limit:
                return False

            # Add current request
            request_times.append(current_time)
            return True

    def block_ip(self, ip, duration):
        """Block IP for specified duration"""
        self.blocked_ips[ip] = time.time() + duration

    def is_ip_blocked(self, ip):
        """Check if IP is currently blocked"""
        if ip in self.blocked_ips:
            if time.time() < self.blocked_ips[ip]:
                return True
            else:
                del self.blocked_ips[ip]
        return False

    def cleanup_old_data(self):
        """Clean up old data to prevent memory leaks"""
        current_time = time.time()
        with self.lock:
            # Clean expired blocked IPs
            expired_ips = [ip for ip, expiry in self.blocked_ips.items() if current_time >= expiry]
            for ip in expired_ips:
                del self.blocked_ips[ip]

            # Clean old request records (keep only last hour)
            for key in list(self.requests.keys()):
                request_times = self.requests[key]
                while request_times and request_times[0] <= current_time - 3600:
                    request_times.popleft()
                if not request_times:
                    del self.requests[key]

# Global rate limiter instance
rate_limiter = RateLimiter()

def get_client_key():
    """Generate unique key for rate limiting"""
    ip = request.remote_addr or 'unknown'
    user_agent = request.headers.get('User-Agent', '')
    return f"{ip}:{hash(user_agent)}"

def apply_rate_limit(endpoint_type='api'):
    """
    Apply rate limiting based on endpoint type
    Uses configuration from security_settings
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_key = get_client_key()
            ip = request.remote_addr

            # Check if IP is blocked
            if rate_limiter.is_ip_blocked(ip):
                logger.warning(f"Blocked IP attempted access: {ip}")
                abort(429)

            # Get rate limit config for endpoint type
            rate_config = security_settings.get_rate_limit_config(endpoint_type)
            if not rate_config:
                return f(*args, **kwargs)

            # Check rate limit
            if not rate_limiter.is_allowed(client_key, rate_config['limit'], rate_config['window']):
                # Log security event
                from security.monitoring.logging import log_security_event
                log_security_event(
                    'RATE_LIMIT_EXCEEDED',
                    f'Endpoint: {endpoint_type}, Client: {client_key}',
                    'WARNING',
                    {'ip': ip, 'endpoint': request.endpoint}
                )

                # Block IP if configured
                if rate_config.get('block_duration'):
                    rate_limiter.block_ip(ip, rate_config['block_duration'])

                abort(429)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit_api(f):
    """Convenience decorator for API endpoints"""
    return apply_rate_limit('api')(f)

def rate_limit_search(f):
    """Convenience decorator for search endpoints"""
    return apply_rate_limit('search')(f)

def rate_limit_upload(f):
    """Convenience decorator for upload endpoints"""
    return apply_rate_limit('upload')(f)