import redis
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from security.monitoring.logging import security_monitor
from security_config import setup_enhanced_logging

# Global extension objects
limiter = None
security_logger = None
redis_client = None

def init_extensions(app):
    """Initialize Flask extensions with app context"""
    global limiter, security_logger, redis_client

    # Setup enhanced logging first
    security_logger = setup_enhanced_logging()

    # Initialize Redis
    redis_client = init_redis(app)

    # Initialize rate limiter
    limiter = init_rate_limiter(app)

    # Initialize security monitoring
    security_monitor.init_app(app)

    return {
        'limiter': limiter,
        'security_logger': security_logger,
        'redis_client': redis_client,
        'security_monitor': security_monitor
    }

def init_redis(app):
    """Initialize Redis connection"""
    try:
        redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379')
        client = redis.Redis.from_url(redis_url)
        client.ping()  # Test connection
        app.logger.info("Redis connection established")
        return client
    except Exception as e:
        app.logger.error("Redis connection failed: %s", e)
        return None

def init_rate_limiter(app):
    """Initialize Flask-Limiter"""
    redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379')

    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        storage_uri=redis_url,
        default_limits=app.config.get('RATE_LIMITS', {}).get('default', ['100 per hour']),
        strategy="sliding-window-counter",
        headers_enabled=True,
        swallow_errors=True,  # Don't break app if Redis is down
    )

    app.logger.info("Rate limiter initialized")
    return limiter

def get_extensions():
    """Get initialized extensions"""
    return {
        'limiter': limiter,
        'security_logger': security_logger,
        'redis_client': redis_client,
        'security_monitor': security_monitor
    }
