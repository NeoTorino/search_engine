"""
Enhanced security core module with unified validation
"""
import re
import unicodedata
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import logging
from flask import request
from security.core.patterns import security_patterns

# Configure security logger
security_logger = logging.getLogger('security')

@dataclass
class ValidationResult:
    """Result of security validation"""
    is_valid: bool
    sanitized_value: Any
    threats_detected: List[str]
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    original_value: Any

class SecurityValidator:
    """Unified security validator for all input types"""

    def __init__(self):
        self.patterns = security_patterns

    def validate_input(self,
                      value: Any,
                      input_type: str = 'general',
                      max_length: int = 1000,
                      allow_html: bool = False,
                      custom_patterns: List[str] = None) -> ValidationResult:
        """
        Comprehensive input validation against all security patterns

        Args:
            value: Input value to validate
            input_type: Type of input (general, search, filter, filename, etc.)
            max_length: Maximum allowed length
            allow_html: Whether to allow basic HTML tags
            custom_patterns: Additional pattern groups to check

        Returns:
            ValidationResult with validation status and sanitized value
        """
        if not isinstance(value, str):
            if value is None:
                return ValidationResult(True, "", [], "LOW", value)
            value = str(value)

        original_value = value
        threats_detected = []
        severity = "LOW"

        # Check all dangerous patterns at once
        threat_results = self._check_all_threats(value, custom_patterns)
        threats_detected.extend(threat_results['threats'])
        severity = threat_results['max_severity']

        # Determine if input is valid based on threats
        is_valid = severity not in ['HIGH', 'CRITICAL']

        # Sanitize the input if it's not critically dangerous
        if severity != 'CRITICAL':
            sanitized_value = self._sanitize_input(
                value, input_type, max_length, allow_html
            )
        else:
            sanitized_value = ""

        return ValidationResult(
            is_valid=is_valid,
            sanitized_value=sanitized_value,
            threats_detected=threats_detected,
            severity=severity,
            original_value=original_value
        )

    def _check_all_threats(self, text: str, custom_patterns: List[str] = None) -> Dict[str, Any]:
        """Check text against all threat patterns and return comprehensive results"""
        threats = []
        max_severity = "LOW"

        # Define pattern groups with their severity levels
        pattern_groups = {
            'dangerous_strings': 'HIGH',
            'sql_injection': 'CRITICAL',
            'nosql_injection': 'HIGH',
            'opensearch_injection': 'HIGH',
            'command_injection': 'CRITICAL',
            'path_traversal': 'HIGH',
            'ldap_injection': 'MEDIUM',
            'xxe_injection': 'HIGH',
            'template_injection': 'HIGH',
            'json_injection': 'MEDIUM'
        }

        # Add custom patterns if provided
        if custom_patterns:
            for pattern in custom_patterns:
                pattern_groups[pattern] = 'MEDIUM'

        # Check each pattern group
        for group_name, severity in pattern_groups.items():
            if self.patterns.check_patterns(text, group_name):
                threats.append(f"{group_name}_detected")
                max_severity = self._get_higher_severity(max_severity, severity)

        # Additional checks
        if self._check_suspicious_characteristics(text):
            threats.append("suspicious_characteristics")
            max_severity = self._get_higher_severity(max_severity, "MEDIUM")

        return {
            'threats': threats,
            'max_severity': max_severity
        }

    def _check_suspicious_characteristics(self, text: str) -> bool:
        """Check for suspicious characteristics in input"""
        # Too many special characters
        special_char_ratio = self.patterns.count_special_chars(text) / len(text) if text else 0
        if special_char_ratio > 0.5:
            return True

        # Extremely long input
        if len(text) > 10000:
            return True

        # Contains null bytes or control characters
        if any(ord(char) < 32 and char not in '\t\n\r' for char in text):
            return True

        return False

    def _get_higher_severity(self, current: str, new: str) -> str:
        """Return the higher severity level"""
        severity_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        return current if severity_order[current] >= severity_order[new] else new

    def _sanitize_input(self, text: str, input_type: str, max_length: int, allow_html: bool) -> str:
        """Sanitize input based on type and configuration"""
        if not text:
            return ""

        # Input type specific sanitization
        if input_type == 'search':
            return self._sanitize_search_input(text, max_length)
        elif input_type == 'filename':
            return self.patterns.sanitize_filename(text)
        elif input_type == 'email':
            return text.strip().lower() if self.patterns.validate_email(text) else ""
        elif input_type == 'filter':
            return self._sanitize_filter_input(text, max_length)
        else:
            return self._sanitize_general_input(text, max_length, allow_html)

    def _sanitize_search_input(self, text: str, max_length: int) -> str:
        """Sanitize search query input"""

        # Remove script-related content
        script_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'on\w+\s*=',
            r'eval\s*\(',
            r'setTimeout\s*\(',
            r'setInterval\s*\('
        ]

        # Remove dangerous patterns
        sanitized = text

        for pattern in script_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)

        # Remove HTML tags
        sanitized = self.patterns.get_pattern('html_tags').sub('', sanitized)

        # Limit length and clean whitespace
        sanitized = sanitized[:max_length].strip()

        return sanitized

    def _sanitize_filter_input(self, text: str, max_length: int) -> str:
        """Sanitize filter value input"""
        # Very strict sanitization for filters

        # Keep only alphanumeric, spaces, hyphens, underscores, and dots
        sanitized = re.sub(r'[^\w\s\-_.]', '', text)
        sanitized = sanitized[:max_length].strip()

        return sanitized

    def _sanitize_general_input(self, text: str, max_length: int, allow_html: bool) -> str:
        """General input sanitization"""

        # Normalize unicode
        sanitized = unicodedata.normalize('NFKC', text)

        # Remove null bytes and control characters
        sanitized = sanitized.replace('\x00', '')
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\t\n\r')

        if not allow_html:
            # Remove all HTML/XML tags
            sanitized = self.patterns.get_pattern('html_tags').sub('', sanitized)

        # Remove dangerous script content
        script_patterns = [
            r'javascript:', r'vbscript:', r'data:', r'file:',
            r'eval\s*\(', r'setTimeout\s*\(', r'setInterval\s*\('
        ]

        for pattern in script_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)

        # Limit length
        sanitized = sanitized[:max_length].strip()

        return sanitized

# Global validator instance
security_validator = SecurityValidator()

def validate_all_inputs(data: Dict[str, Any],
                       validation_config: Dict[str, Dict] = None) -> Dict[str, ValidationResult]:
    """
    Validate all inputs in a dictionary (e.g., request.json, request.args)

    Args:
        data: Dictionary of input data to validate
        validation_config: Configuration for each field

    Returns:
        Dictionary mapping field names to ValidationResult objects
    """
    results = {}

    if not validation_config:
        validation_config = {}

    for key, value in data.items():
        # Get configuration for this field
        field_config = validation_config.get(key, {})

        # Validate the input
        result = security_validator.validate_input(
            value=value,
            input_type=field_config.get('type', 'general'),
            max_length=field_config.get('max_length', 1000),
            allow_html=field_config.get('allow_html', False),
            custom_patterns=field_config.get('custom_patterns')
        )

        results[key] = result

        # Log security events for invalid inputs
        if not result.is_valid:
            security_logger.warning(
                "Security validation failed for field '%s': %s (severity: %s)",
                key, result.threats_detected, result.severity
            )

    return results

def check_request_security(validation_config: Dict[str, Dict] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Comprehensive security check for Flask request

    Args:
        validation_config: Field-specific validation configuration

    Returns:
        Tuple of (is_safe, sanitized_data)
    """

    all_data = {}

    # Collect all request data
    if request.args:
        all_data.update(request.args.to_dict(flat=False))

    if request.form:
        all_data.update(request.form.to_dict(flat=False))

    if request.is_json and request.get_json():
        json_data = request.get_json()
        if isinstance(json_data, dict):
            all_data.update(json_data)

    # Flatten list values to strings for validation
    flattened_data = {}
    for key, value in all_data.items():
        if isinstance(value, list):
            # Join list values with comma for validation
            flattened_data[key] = ', '.join(str(v) for v in value)
        else:
            flattened_data[key] = value

    # Validate all inputs
    validation_results = validate_all_inputs(flattened_data, validation_config)

    # Check if request is safe
    is_safe = all(result.is_valid for result in validation_results.values())

    # Create sanitized data dictionary
    sanitized_data = {
        key: result.sanitized_value
        for key, result in validation_results.items()
    }

    # Log comprehensive security event if threats detected
    threats_found = []
    for key, result in validation_results.items():
        if result.threats_detected:
            threats_found.extend([f"{key}:{threat}" for threat in result.threats_detected])

    if threats_found:
        security_logger.error(
            "Security threats detected in request: %s",
            threats_found
        )

    return is_safe, sanitized_data
