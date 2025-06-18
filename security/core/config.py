# security/core/config.py


class SecurityMonitorConfig:
    """Configuration for security monitoring"""

    # Rate limiting thresholds
    RATE_LIMIT_THRESHOLD = 50  # requests per 5 minutes
    SUSPICIOUS_PATTERN_THRESHOLD = 5  # suspicious requests per hour
    CRITICAL_THREAT_THRESHOLD = 3  # critical threats per hour

    # Memory limits
    MAX_FAILED_REQUESTS_PER_IP = 100
    REQUEST_HISTORY_RETENTION_HOURS = 24

    # Log file settings
    LOG_FILE_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    LOG_DIRECTORY = 'logs'

    # OpenObserve settings
    OPENOBSERVE_TIMEOUT = 5
    OPENOBSERVE_STREAM = "security_events"

    # Cleanup intervals
    CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour

    # Health check endpoints to skip monitoring
    SKIP_ENDPOINTS = ['main.health_check', 'health_check', 'metrics']

    @classmethod
    def from_flask_config(cls, app_config):
        """Create config from Flask app config"""
        config = cls()

        # Override defaults with app config if present
        config.RATE_LIMIT_THRESHOLD = app_config.get('SECURITY_RATE_LIMIT_THRESHOLD', cls.RATE_LIMIT_THRESHOLD)
        config.LOG_DIRECTORY = app_config.get('SECURITY_LOG_DIRECTORY', cls.LOG_DIRECTORY)
        # ... other overrides

        return config
