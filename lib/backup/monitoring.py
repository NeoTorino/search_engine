
import re
import os
import time
import json
import logging
import threading
from datetime import datetime
from collections import defaultdict, deque
from logging.handlers import RotatingFileHandler
from threading import Lock
from typing import Dict, Optional
from flask import request
import requests

class SecurityMonitor:
    """
    Centralized security monitoring and alerting system
    """

    def __init__(self, app=None):
        self.app = app
        self.failed_requests = defaultdict(lambda: deque(maxlen=100))
        self.request_counts = defaultdict(lambda: defaultdict(int))
        self.suspicious_ips = set()
        self.blocked_ips = set()
        self.lock = Lock()

        # OpenObserve configuration
        self.openobserve_url = None
        self.openobserve_auth = None
        self.openobserve_stream = "security_events"

        # Threat detection thresholds
        self.RATE_LIMIT_THRESHOLD = 50  # requests per 5 minutes
        self.SUSPICIOUS_PATTERN_THRESHOLD = 5  # suspicious requests per hour
        self.CRITICAL_THREAT_THRESHOLD = 3  # critical threats per hour

        # Configure logging
        self.setup_logging()

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app

        # Configure OpenObserve if available
        self.openobserve_url = app.config.get('OPENOBSERVE_URL')
        self.openobserve_auth = app.config.get('OPENOBSERVE_AUTH')

        # Register before_request handler
        app.before_request(self.monitor_request)

        # Setup periodic cleanup
        self.setup_periodic_cleanup()

    def setup_logging(self):
        """Setup security logging with proper formatting"""
        self.logger = logging.getLogger('security_monitor')
        self.logger.setLevel(logging.INFO)

        # Prevent duplicate handlers
        if self.logger.handlers:
            return

         # Check if the logs directory exists, and create it if it doesn't
        log_directory = 'logs'
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)

        # File handler with rotation
        try:
            file_handler = RotatingFileHandler(
                'logs/security_events.log',
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.INFO)
        except Exception:
            # Fallback to regular file handler
            file_handler = logging.FileHandler('logs/security_events.log')
            file_handler.setLevel(logging.INFO)

        # Console handler for critical events only
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)

        # Formatter with more context
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def log_security_event(self, event_type: str, details: str, 
                          severity: str = "WARNING", 
                          request_info: Optional[Dict] = None):
        """
        Log security events with structured data and threat assessment
        """
        try:
            if request_info is None and request:
                request_info = {
                    'ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'url': request.url,
                    'referrer': request.referrer,
                    'content_type': request.headers.get('Content-Type', ''),
                    'content_length': request.headers.get('Content-Length', ''),
                    'x_forwarded_for': request.headers.get('X-Forwarded-For', ''),
                    'timestamp': datetime.utcnow().isoformat()
                }

            event_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'details': details,
                'severity': severity,
                'request_info': request_info or {}
            }

            # Create structured log message
            log_message = json.dumps(event_data, separators=(',', ':'))

            # Log based on severity
            if severity == "CRITICAL":
                self.logger.critical(log_message)
            elif severity == "ERROR":
                self.logger.error(log_message)
            elif severity == "WARNING":
                self.logger.warning(log_message)
            else:
                self.logger.info(log_message)

            # Send to OpenObserve if configured
            self.send_to_openobserve(event_data)

            # Check if we need to take action
            if request_info:
                self.check_for_threats(event_type, request_info)

        except Exception as e:
            # Fallback logging to prevent security monitoring from breaking the app
            try:
                self.logger.error("Security monitoring error: %s", e)
            except Exception as er:
                print("CRITICAL: Security monitoring completely failed: %s", er)

    def send_to_openobserve(self, event_data: Dict):
        """
        Send security events to OpenObserve (non-blocking)
        """
        if not self.openobserve_url or not self.openobserve_auth:
            return

        try:
            def send_async():
                try:
                    url = f"{self.openobserve_url}/api/default/{self.openobserve_stream}/_json"
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': f'Basic {self.openobserve_auth}'
                    }

                    response = requests.post(
                        url,
                        json=[event_data],
                        headers=headers,
                        timeout=5
                    )

                    if response.status_code != 200:
                        self.logger.warning("OpenObserve send failed: %s", response.status_code)

                except Exception as e:
                    self.logger.warning("OpenObserve send error: %s", e)

            # Send in background thread
            thread = threading.Thread(target=send_async, daemon=True)
            thread.start()

        except Exception as e:
            self.logger.warning("OpenObserve async send setup failed: %s", e)

    def monitor_request(self):
        """
        Monitor incoming requests for suspicious activity
        """
        if not request:
            return

        try:
            ip = request.remote_addr or 'unknown'
            current_time = time.time()

            # Skip monitoring for health checks
            if request.endpoint in ['main.health_check', 'health_check']:
                return

            with self.lock:
                # Track request patterns
                self.request_counts[ip]['total'] += 1
                self.request_counts[ip]['last_request'] = current_time

                # Check if IP is blocked
                if ip in self.blocked_ips:
                    self.log_security_event(
                        "BLOCKED_IP_REQUEST",
                        f"Request from blocked IP: {ip}",
                        severity="ERROR"
                    )
                    return

                # Check for suspicious patterns in request
                if self.is_suspicious_request(request):
                    self.log_security_event(
                        "SUSPICIOUS_REQUEST", 
                        f"Suspicious pattern detected - URL: {request.url[:200]}",
                        severity="WARNING"
                    )
                    self.failed_requests[ip].append(current_time)

                # Check for high frequency requests
                self.check_rate_limiting(ip, current_time)

                # Check for known attack patterns
                self.check_attack_patterns(request)

        except Exception as e:
            # Don't let monitoring break the application
            try:
                self.logger.error("Request monitoring error: %s", e)
            except:
                pass

    def is_suspicious_request(self, req) -> bool:
        """
        Check if request contains suspicious patterns
        """
        try:
            # Expanded suspicious patterns
            suspicious_patterns = [
                # SQL Injection
                'union+select', 'union select', 'drop+table', 'drop table',
                'insert+into', 'delete+from', 'update+set',
                # XSS
                '<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=', 
                'onclick=', 'onmouseover=', 'eval(', 'expression(',
                # Path Traversal
                '../../../', '..\\..\\..\\', '../..', '..\\..\\',
                # System Commands
                'cmd.exe', '/bin/sh', '/etc/passwd', '/proc/version',
                # Code Injection
                'base64_decode', 'file_get_contents', 'system(', 'exec(',
                'shell_exec', 'passthru', 'phpinfo()', '<?php',
                # WordPress specific
                'wp-admin', 'wp-login', 'wp-config', 'wp-content',
                # Config files
                '.env', 'config.php', 'database.php', 'settings.php',
                # Admin interfaces
                '/admin', '/administrator', '/phpmyadmin', '/mysql',
                # Common exploits
                'null%00', '%00', '\x00', 'sleep(', 'waitfor delay'
            ]

            # Check URL, query string, and headers
            url_lower = req.url.lower()
            query_string = req.query_string.decode('utf-8', errors='ignore').lower()
            user_agent = req.headers.get('User-Agent', '').lower()

            # Combine all text to check
            combined_text = url_lower + ' ' + query_string + ' ' + user_agent

            for pattern in suspicious_patterns:
                if pattern in combined_text:
                    return True

            # Check for unusual request methods
            if req.method not in ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS']:
                return True

            # Check for suspicious User-Agent patterns
            suspicious_ua_patterns = [
                'sqlmap', 'nikto', 'nmap', 'masscan', 'zap', 'burp',
                'bot', 'crawler', 'spider', 'scraper', 'python-requests'
            ]

            for pattern in suspicious_ua_patterns:
                if pattern in user_agent:
                    return True

            return False

        except Exception:
            return False

    def check_rate_limiting(self, ip: str, current_time: float):
        """
        Check for rate limiting violations with sliding window
        """
        try:
            # Clean old entries (older than 5 minutes)
            cutoff_time = current_time - 300
            while self.failed_requests[ip] and self.failed_requests[ip][0] < cutoff_time:
                self.failed_requests[ip].popleft()

            # Check request frequency (all requests in last 5 minutes)
            recent_requests = sum(1 for timestamp in self.failed_requests[ip]
                                if timestamp > current_time - 300)

            if recent_requests > self.RATE_LIMIT_THRESHOLD:
                self.log_security_event(
                    "HIGH_FREQUENCY_REQUESTS",
                    f"IP {ip} made {recent_requests} requests in 5 minutes",
                    severity="ERROR"
                )
                self.suspicious_ips.add(ip)

                # Block IP if it's extremely abusive
                if recent_requests > self.RATE_LIMIT_THRESHOLD * 2:
                    self.blocked_ips.add(ip)
                    self.log_security_event(
                        "IP_BLOCKED",
                        f"IP {ip} blocked for excessive requests: {recent_requests}",
                        severity="CRITICAL"
                    )

        except Exception as e:
            self.logger.error("Rate limiting check error: %s", e)

    def check_attack_patterns(self, request):
        """
        Check for specific attack patterns with regex
        """
        try:
            # SQL Injection patterns (more comprehensive)
            sql_patterns = [
                r"union\s+select", r"drop\s+table", r"delete\s+from",
                r"insert\s+into", r"update\s+set", r"exec\s*\(",
                r"sp_executesql", r"xp_cmdshell", r"or\s+1\s*=\s*1",
                r"and\s+1\s*=\s*1", r"'\s+or\s+'", r"admin'\s*--"
            ]

            # XSS patterns (more comprehensive)
            xss_patterns = [
                r"<script[^>]*>", r"javascript\s*:", r"vbscript\s*:",
                r"on\w+\s*=", r"expression\s*\(", r"<iframe[^>]*>",
                r"<object[^>]*>", r"<embed[^>]*>", r"<form[^>]*>"
            ]

            # Path traversal patterns
            path_patterns = [
                r"\.\./", r"\.\.\\", r"etc/passwd", r"boot\.ini",
                r"windows/system32", r"/proc/", r"\.\.%2f", r"\.\.%5c"
            ]

            # Command injection patterns
            cmd_patterns = [
                r";\s*cat\s+", r";\s*ls\s+", r";\s*id\s*;", r";\s*pwd\s*;",
                r"\|\s*cat\s+", r"\|\s*ls\s+", r"&&\s*cat\s+", r"&\s*dir\s+"
            ]

            all_patterns = {
                'SQL_INJECTION': sql_patterns,
                'XSS_ATTEMPT': xss_patterns,
                'PATH_TRAVERSAL': path_patterns,
                'COMMAND_INJECTION': cmd_patterns
            }

            # Check URL and query parameters
            full_url = request.url.lower()
            query_string = request.query_string.decode('utf-8', errors='ignore').lower()
            combined_input = full_url + ' ' + query_string

            for attack_type, patterns in all_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, combined_input, re.IGNORECASE):
                        self.log_security_event(
                            attack_type,
                            f"Attack pattern detected: {pattern[:50]}",
                            severity="CRITICAL"
                        )

                        # Add to suspicious IPs immediately for critical attacks
                        if request.remote_addr:
                            self.suspicious_ips.add(request.remote_addr)
                        return

        except Exception as e:
            self.logger.error("Attack pattern check error: %s", e)

    def check_for_threats(self, event_type: str, request_info: Dict):
        """
        Assess threat level and take appropriate action
        """
        try:
            if not request_info:
                return

            ip = request_info.get('ip')
            if not ip:
                return

            # Critical events that should trigger immediate action
            critical_events = [
                'SQL_INJECTION', 'XSS_ATTEMPT', 'PATH_TRAVERSAL',
                'COMMAND_INJECTION', 'AUTHENTICATION_BYPASS', 
                'PRIVILEGE_ESCALATION'
            ]

            if event_type in critical_events:
                with self.lock:
                    self.suspicious_ips.add(ip)

                    # Check if this IP has multiple critical events
                    critical_count = sum(1 for timestamp in self.failed_requests[ip] 
                                       if timestamp > time.time() - 3600)  # Last hour

                    if critical_count >= self.CRITICAL_THREAT_THRESHOLD:
                        self.blocked_ips.add(ip)
                        self.log_security_event(
                            "CRITICAL_THREAT_BLOCKED",
                            f"IP {ip} blocked after {critical_count} critical threats",
                            severity="CRITICAL"
                        )

        except Exception as e:
            self.logger.error("Threat assessment error: %s", e)

    def setup_periodic_cleanup(self):
        """
        Setup periodic cleanup of old data
        """

        def cleanup():
            while True:
                time.sleep(3600)  # Run every hour
                self.cleanup_old_data()

        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()

    def cleanup_old_data(self):
        """
        Clean up old monitoring data
        """
        current_time = time.time()
        cutoff_time = current_time - 86400  # 24 hours

        with self.lock:
            # Clean request counts
            for ip in list(self.request_counts.keys()):
                if self.request_counts[ip].get('last_request', 0) < cutoff_time:
                    del self.request_counts[ip]

            # Clean failed requests
            for ip in list(self.failed_requests.keys()):
                if not self.failed_requests[ip]:
                    del self.failed_requests[ip]

    def get_security_stats(self) -> Dict:
        """
        Get current security statistics
        """
        with self.lock:
            stats = {
                'monitored_ips': len(self.request_counts),
                'suspicious_ips': len(self.suspicious_ips),
                'total_requests': sum(
                    counts['total'] for counts in self.request_counts.values()
                ),
                'active_threats': len([
                    ip for ip, requests in self.failed_requests.items()
                    if len(requests) > 10
                ])
            }

        return stats

# Global instance
security_monitor = SecurityMonitor()

# Convenience function for logging
def log_security_event(event_type: str, details: str,
                      severity: str = "WARNING",
                      request_info: Optional[Dict] = None):
    """
    Convenience function to log security events
    """
    security_monitor.log_security_event(event_type, details, severity, request_info)
