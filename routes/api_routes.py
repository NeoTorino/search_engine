import logging
from flask import Blueprint, request, jsonify, abort, current_app
from functools import wraps

from services.insights_service import (
    get_combined_insights, get_organizations_insights
)
from utils.security import (
    validate_search_query, validate_filter_values, 
    validate_request_size, detect_bot_behavior, validate_pagination_params
)
from utils.monitoring import log_security_event
from security_config import SecurityConfig

api = Blueprint('api', __name__, url_prefix='/api')

security_logger = logging.getLogger('security')

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

def get_search_params():
    """Extract and return standardized search parameters from request with comprehensive security validation"""
    try:
        # Validate search query
        raw_query = request.args.get('q', '')
        is_valid, sanitized_query = validate_search_query(raw_query)
        if not is_valid:
            security_logger.warning("Invalid search query blocked: %s", raw_query)
            log_security_event("INVALID_SEARCH_QUERY", f"Blocked query: {raw_query}")
            sanitized_query = ''
        
        # Validate filter parameters
        countries = validate_filter_values(
            request.args.getlist('country'), 
            max_items=20  # Limit number of countries
        )
        
        organizations = validate_filter_values(
            request.args.getlist('organization'), 
            max_items=50  # Limit number of organizations
        )
        
        sources = validate_filter_values(
            request.args.getlist('source'), 
            max_items=10  # Limit number of sources
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
        
        # Validate pagination if present
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 20, type=int)
        offset, limit, error = validate_pagination_params(offset, limit, max_limit=100, max_offset=1000)
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

@api.route("/insights")
@rate_limit_decorator('api')
@security_check()
@validate_request_size(max_size=1024*10)  # 10KB limit
def combined_insights():
    """Get all insights data in a single response: overview, jobs per day, top countries, and word cloud"""
    try:
        search_params = get_search_params()
        
        # Additional validation: ensure we have some reasonable parameters
        total_filters = len(search_params['countries']) + len(search_params['organizations']) + len(search_params['sources'])
        if total_filters > 100:  # Prevent excessive filter combinations
            log_security_event("EXCESSIVE_FILTERS", f"Total filters: {total_filters}")
            return jsonify({"error": "Too many filter parameters"}), 400
        
        # Word cloud might be more resource intensive, add extra checks
        if len(search_params['query']) > 100:
            log_security_event("LONG_INSIGHTS_QUERY", f"Query length: {len(search_params['query'])}")
            return jsonify({"error": "Query too long for insights analysis"}), 400
        
        # Get combined insights data
        data = get_combined_insights(search_params)
        
        # Validate response data before sending
        if not isinstance(data, dict):
            log_security_event("INVALID_RESPONSE_DATA", "Combined insights data is not a dictionary")
            return jsonify({"error": "Invalid response format"}), 500
        
        # Validate structure of combined response
        required_keys = ['overview', 'jobs_per_day', 'top_countries', 'word_cloud']
        if not all(key in data for key in required_keys):
            log_security_event("INCOMPLETE_INSIGHTS_DATA", f"Missing keys in response: {set(required_keys) - set(data.keys())}")
            return jsonify({"error": "Incomplete insights data"}), 500
            
        return jsonify(data)
        
    except ValueError as e:
        security_logger.warning("Invalid parameters in combined insights: %s", e)
        return jsonify({"error": "Invalid parameters"}), 400
    except Exception as e:
        security_logger.error("Error in combined insights: %s", e)
        log_security_event("INSIGHTS_ERROR", f"Combined insights error: {e}")
        return jsonify({"error": "Failed to load insights data"}), 500


@api.route("/insights/organizations")
@rate_limit_decorator('api')
@security_check()
@validate_request_size(max_size=1024*10)
def insights_organizations():
    """Get organizations with job counts and last update dates"""
    try:
        search_params = get_search_params()
        
        # Additional validation
        total_filters = len(search_params['countries']) + len(search_params['organizations']) + len(search_params['sources'])
        if total_filters > 100:
            log_security_event("EXCESSIVE_FILTERS", f"Total filters: {total_filters}")
            return jsonify({"error": "Too many filter parameters"}), 400
        
        data = get_organizations_insights(search_params)
        
        # Validate response data
        if not isinstance(data, (dict, list)):
            log_security_event("INVALID_RESPONSE_DATA", "Organizations data is invalid")
            return jsonify({"error": "Invalid response format"}), 500
            
        return jsonify(data)
        
    except ValueError as e:
        security_logger.warning("Invalid parameters in organizations insights: %s", e)
        return jsonify({"error": "Invalid parameters"}), 400
    except Exception as e:
        security_logger.error("Error in organizations insights: %s", e)
        log_security_event("INSIGHTS_ERROR", f"Organizations insights error: {e}")
        return jsonify({"error": "Failed to load organizations data"}), 500