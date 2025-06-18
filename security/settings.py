"""
Centralized Security Configuration
All security settings and configurations in one place
"""
import os
from typing import Dict, List

class SecuritySettings:
    """Centralized security configuration class"""

    # === RATE LIMITING CONFIGURATION ===
    RATE_LIMITS = {
        'default': ["2000 per day", "200 per hour", "20 per minute"],
        'search': ["1000 per day", "100 per hour", "10 per minute"],
        'api': ["500 per day", "50 per hour", "5 per minute"],
        'auth': ["10 per hour", "3 per minute"],
    }

    # === INPUT VALIDATION LIMITS ===
    MAX_QUERY_LENGTH = 200
    MAX_FILTER_ITEMS = {
        'countries': 20,
        'organizations': 50,
        'sources': 10,
        'default': 10
    }
    MAX_REQUEST_SIZE = 1024 * 1024  # 1MB
    MAX_JSON_SIZE = 10000
    MAX_PAGINATION_OFFSET = 10000
    MAX_PAGINATION_LIMIT = 100
    MAX_DATE_RANGE_DAYS = 365
    MAX_STRING_LENGTH = 1000
    MAX_FILENAME_LENGTH = 255

    # === SECURITY MONITORING ===
    SUSPICIOUS_REQUEST_THRESHOLD = 50  # per hour
    BLOCKED_IP_DURATION = 3600  # 1 hour in seconds
    MAX_FAILED_ATTEMPTS = 5

    # === ALLOWED VALUES ===
    ALLOWED_FILE_EXTENSIONS = {'.txt', '.pdf', '.doc', '.docx'}
    ALLOWED_CONTENT_TYPES = [
        'application/json',
        'application/x-www-form-urlencoded',
        'multipart/form-data',
        'text/plain'
    ]
    ALLOWED_HTTP_METHODS = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'}

    # === SENSITIVE ENDPOINTS ===
    SENSITIVE_ENDPOINTS = {
        'api.security_stats',
        'main.stats',
        'admin'
    }

    SKIP_SECURITY_ENDPOINTS = {
        'main.health_check',
        'static'
    }

    # === ENVIRONMENT-SPECIFIC SETTINGS ===
    @classmethod
    def get_allowed_hosts(cls) -> List[str]:
        """Get allowed hosts from environment"""
        return os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

    @classmethod
    def get_redis_url(cls) -> str:
        """Get Redis URL from environment"""
        return os.getenv('REDIS_URL', 'redis://localhost:6379')

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production"""
        return os.getenv('FLASK_ENV') == 'production'

    # === VALIDATION PATTERNS ===
    DANGEROUS_PATTERNS = {
        'script_injection': [
            r'javascript:', r'vbscript:', r'data:', r'file:', r'ftp:',
            r'<script', r'</script', r'eval\s*\(', r'setTimeout\s*\(',
            r'setInterval\s*\(', r'Function\s*\(', r'constructor\s*\(',
            r'__proto__', r'prototype\.', r'\.constructor'
        ],
        'sql_injection': [
            r'union\s+select', r'drop\s+table', r'delete\s+from',
            r'insert\s+into', r'update\s+set', r'exec\s*\(',
        ],
        'opensearch_injection': [
            r'_search\s*\{', r'_bulk\s*\{', r'_delete_by_query',
            r'_update_by_query', r'script\s*:', r'inline\s*:',
            r'source\s*:', r'params\s*:', r'lang\s*:',
        ],
        'command_injection': [
            r';\s*\w+', r'\|\s*\w+', r'&&\s*\w+', r'\$\(', r'`.*`',
        ],
        'path_traversal': [
            r'\.\./', r'\.\.\\', r'/etc/', r'/proc/', r'/sys/',
        ],
        'ldap_injection': [
            r'\(\s*\|', r'\(\s*&', r'\*\s*\)', r'=\s*\*'
        ]
    }

    BOT_PATTERNS = [
        r'bot', r'crawl', r'spider', r'scrape', r'fetch',
        r'curl', r'wget', r'python', r'java', r'go-http',
        r'automated', r'scanner', r'monitor'
    ]

    ATTACK_TOOL_PATTERNS = [
        'sqlmap', 'nikto', 'nmap', 'masscan', 'zap', 'burp',
        'dirbuster', 'gobuster', 'wfuzz', 'ffuf', 'hydra'
    ]

    # === HTML SANITIZATION ===
    ALLOWED_HTML_TAGS = ['b', 'i', 'em', 'strong', 'p', 'br']
    ALLOWED_HTML_ATTRIBUTES = {}

    # === OPENSEARCH SECURITY ===
    SAFE_OPENSEARCH_FIELDS = [
        'date_posted', 'title', 'organization', 'country',
        'source', 'created_at', 'updated_at', '_score'
    ]

    SAFE_AGGREGATION_TYPES = [
        'terms', 'date_histogram', 'histogram', 'range',
        'sum', 'avg', 'min', 'max', 'count', 'cardinality',
        'percentiles', 'stats', 'extended_stats'
    ]

    DANGEROUS_OPENSEARCH_FIELDS = [
        '_source', '_id', '_type', '_index', '_score',
        '_script', '_inline', '_file'
    ]

    # === LOGGING CONFIGURATION ===
    LOG_DIRECTORY = 'logs'
    SECURITY_LOG_FILE = 'security.log'
    MAX_LOG_EVENTS_IN_REDIS = 1000

    # === VALIDATION CONFIGURATIONS ===
    FIELD_VALIDATION_CONFIGS = {
        'search_api': {
            'q': {'type': 'search', 'max_length': 200, 'required': False},
            'country': {'type': 'filter', 'max_length': 50, 'required': False, 'is_list': True},
            'organization': {'type': 'filter', 'max_length': 100, 'required': False, 'is_list': True},
            'source': {'type': 'filter', 'max_length': 50, 'required': False, 'is_list': True},
            'limit': {'type': 'numeric', 'max_value': MAX_PAGINATION_LIMIT, 'required': False},
            'offset': {'type': 'numeric', 'max_value': MAX_PAGINATION_OFFSET, 'required': False},
            'date_posted_days': {'type': 'numeric', 'max_value': MAX_DATE_RANGE_DAYS, 'required': False}
        },
        'user_profile': {
            'name': {'type': 'general', 'max_length': 100, 'required': True},
            'email': {'type': 'email', 'max_length': 254, 'required': True},
            'bio': {'type': 'general', 'max_length': 500, 'required': False, 'allow_html': True}
        },
        'file_upload': {
            'filename': {'type': 'filename', 'max_length': 255, 'required': True},
            'description': {'type': 'general', 'max_length': 1000, 'required': False}
        }
    }

# Singleton instance for easy access
security_settings = SecuritySettings()

# Helper functions for common operations
def get_max_filter_items(filter_type: str) -> int:
    """Get max items for a specific filter type"""
    return security_settings.MAX_FILTER_ITEMS.get(filter_type, security_settings.MAX_FILTER_ITEMS['default'])

def is_sensitive_endpoint(endpoint: str) -> bool:
    """Check if endpoint is sensitive"""
    return endpoint in security_settings.SENSITIVE_ENDPOINTS

def should_skip_security(endpoint: str) -> bool:
    """Check if security should be skipped for endpoint"""
    return endpoint in security_settings.SKIP_SECURITY_ENDPOINTS

def get_validation_config(config_name: str) -> Dict:
    """Get validation configuration by name"""
    return security_settings.FIELD_VALIDATION_CONFIGS.get(config_name, {})

def get_all_dangerous_patterns() -> List[str]:
    """Get all dangerous patterns combined"""
    all_patterns = []
    for pattern_list in security_settings.DANGEROUS_PATTERNS.values():
        all_patterns.extend(pattern_list)
    return all_patterns
