"""
Enhanced threat detection module
Consolidates bot detection and other threat detection logic from the original security.py
"""

import re
import time
import logging
from collections import defaultdict
from flask import request
from security.settings import security_settings

logger = logging.getLogger(__name__)

# Global tracking for suspicious activities
suspicious_activities = defaultdict(list)
request_patterns = defaultdict(list)

def detect_bot_behavior(req=None):
    """
    Enhanced bot detection with multiple heuristics
    Uses request object or current Flask request
    """
    if req is None:
        req = request

    if not req:
        return False

    user_agent = req.headers.get('User-Agent', '').lower()

    # Bot patterns from security settings
    bot_patterns = security_settings.get_bot_patterns()

    for pattern in bot_patterns:
        if re.search(pattern, user_agent):
            return True

    # Missing common browser headers
    required_headers = ['accept', 'accept-language', 'accept-encoding']
    missing_headers = sum(1 for header in required_headers if not req.headers.get(header))

    if missing_headers >= 2:  # Missing 2 or more required headers
        return True

    # Suspicious request patterns
    if _check_suspicious_request_patterns(req):
        return True

    # Check request frequency (simple bot detection)
    if _check_request_frequency(req):
        return True

    return False

def _check_suspicious_request_patterns(req):
    """Check for suspicious request patterns"""
    # Too many parameters
    if len(req.args) > 20:
        return True

    # Unusual parameter patterns
    for key, value in req.args.items():
        if len(key) > 100 or (isinstance(value, str) and len(value) > 1000):
            return True

    # Suspicious paths
    suspicious_paths = [
        r'/\.env', r'/config\.', r'/admin', r'/wp-admin',
        r'/phpMyAdmin', r'/manager', r'/console'
    ]

    for pattern in suspicious_paths:
        if re.search(pattern, req.path, re.IGNORECASE):
            return True

    return False

def _check_request_frequency(req):
    """Simple request frequency check"""
    current_time = time.time()
    client_ip = req.remote_addr

    # Clean old requests (older than 1 minute)
    request_patterns[client_ip] = [
        timestamp for timestamp in request_patterns[client_ip]
        if current_time - timestamp < 60
    ]

    # Add current request
    request_patterns[client_ip].append(current_time)

    # Check if too many requests in short time
    if len(request_patterns[client_ip]) > 30:  # More than 30 requests per minute
        return True

    return False

def detect_injection_attempts(data):
    """
    Detect various injection attempts in data
    Returns tuple: (is_malicious, threat_types, severity)
    """
    if not data or not isinstance(data, str):
        return False, [], 'LOW'

    threat_types = []
    max_severity = 'LOW'

    # Get dangerous patterns from settings
    dangerous_patterns = security_settings.get_all_dangerous_patterns()

    for category, patterns in dangerous_patterns.items():
        for pattern in patterns:
            if re.search(pattern, data, re.IGNORECASE):
                threat_types.append(category)
                if category in ['sql_injection', 'script_injection', 'command_injection']:
                    max_severity = 'HIGH'
                elif max_severity == 'LOW':
                    max_severity = 'MEDIUM'

    return len(threat_types) > 0, threat_types, max_severity

def detect_opensearch_injection(query_dict):
    """
    Detect OpenSearch/Elasticsearch injection attempts
    """
    if not isinstance(query_dict, dict):
        return False, []

    threats = []

    # Check for script injection
    script_patterns = [
        r'script\s*:', r'inline\s*:', r'source\s*:',
        r'painless', r'groovy', r'expression'
    ]

    def check_recursive(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key

                # Check key for dangerous patterns
                for pattern in script_patterns:
                    if re.search(pattern, str(key), re.IGNORECASE):
                        threats.append(f"Script in key: {current_path}")

                check_recursive(value, current_path)

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_recursive(item, f"{path}[{i}]")

        elif isinstance(obj, str):
            for pattern in script_patterns:
                if re.search(pattern, obj, re.IGNORECASE):
                    threats.append(f"Script in value: {path}")
                    break

    check_recursive(query_dict)

    return len(threats) > 0, threats

def analyze_request_anomalies(req=None):
    """
    Analyze request for various anomalies
    Returns anomaly score and details
    """
    if req is None:
        req = request

    if not req:
        return 0, []

    anomaly_score = 0
    anomalies = []

    # Check user agent anomalies
    user_agent = req.headers.get('User-Agent', '')
    if not user_agent:
        anomaly_score += 20
        anomalies.append('Missing User-Agent')
    elif len(user_agent) > 500:
        anomaly_score += 15
        anomalies.append('Unusually long User-Agent')

    # Check header anomalies
    headers = req.headers
    if len(headers) < 3:
        anomaly_score += 15
        anomalies.append('Too few headers')
    elif len(headers) > 30:
        anomaly_score += 10
        anomalies.append('Too many headers')

    # Check for unusual header values
    for header_name, header_value in headers:
        if len(header_value) > 1000:
            anomaly_score += 10
            anomalies.append(f'Large header: {header_name}')

    # Check request size anomalies
    if req.content_length:
        if req.content_length > 10 * 1024 * 1024:  # 10MB
            anomaly_score += 25
            anomalies.append('Very large request')
        elif req.content_length > 1024 * 1024:  # 1MB
            anomaly_score += 10
            anomalies.append('Large request')

    # Check parameter anomalies
    if len(req.args) > 20:
        anomaly_score += 15
        anomalies.append('Too many parameters')

    return anomaly_score, anomalies

def is_suspicious_ip(ip):
    """
    Check if IP has suspicious activity history
    Simple implementation using in-memory tracking
    """
    current_time = time.time()

    # Clean old activities (older than 1 hour)
    suspicious_activities[ip] = [
        timestamp for timestamp in suspicious_activities[ip]
        if current_time - timestamp < 3600
    ]

    # Check if IP has multiple suspicious activities
    return len(suspicious_activities[ip]) > 5

def mark_suspicious_activity(ip, activity_type='general'):
    """
    Mark IP as having suspicious activity
    """
    current_time = time.time()
    suspicious_activities[ip].append(current_time)

    logger.warning(f"Suspicious activity marked for IP {ip}: {activity_type}")

def get_threat_level(anomaly_score, threat_types):
    """
    Calculate overall threat level based on anomaly score and threat types
    """
    if not threat_types and anomaly_score < 20:
        return 'LOW'
    elif 'script_injection' in threat_types or 'command_injection' in threat_types:
        return 'CRITICAL'
    elif 'sql_injection' in threat_types or anomaly_score > 50:
        return 'HIGH'
    elif threat_types or anomaly_score > 30:
        return 'MEDIUM'
    else:
        return 'LOW'

def cleanup_detection_data():
    """
    Clean up old detection data to prevent memory leaks
    Should be called periodically
    """
    current_time = time.time()

    # Clean request patterns (keep last hour)
    for ip in list(request_patterns.keys()):
        request_patterns[ip] = [
            timestamp for timestamp in request_patterns[ip]
            if current_time - timestamp < 3600
        ]
        if not request_patterns[ip]:
            del request_patterns[ip]

    # Clean suspicious activities (keep last 24 hours)
    for ip in list(suspicious_activities.keys()):
        suspicious_activities[ip] = [
            timestamp for timestamp in suspicious_activities[ip]
            if current_time - timestamp < 86400
        ]
        if not suspicious_activities[ip]:
            del suspicious_activities[ip]
