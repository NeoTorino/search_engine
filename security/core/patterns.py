"""
Centralized security patterns and compiled regex for performance optimization
"""
import re
from typing import List, Pattern

class SecurityPatterns:
    """Centralized security patterns with pre-compiled regex for performance"""

    def __init__(self):
        self._patterns = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all security patterns for performance"""

        # Dangerous string patterns
        self._patterns['dangerous_strings'] = [
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'vbscript:', re.IGNORECASE),
            re.compile(r'data:', re.IGNORECASE),
            re.compile(r'file:', re.IGNORECASE),
            re.compile(r'ftp:', re.IGNORECASE),
            re.compile(r'<script', re.IGNORECASE),
            re.compile(r'</script', re.IGNORECASE),
            re.compile(r'eval\s*\(', re.IGNORECASE),
            re.compile(r'setTimeout\s*\(', re.IGNORECASE),
            re.compile(r'setInterval\s*\(', re.IGNORECASE),
            re.compile(r'Function\s*\(', re.IGNORECASE),
            re.compile(r'constructor\s*\(', re.IGNORECASE),
            re.compile(r'__proto__', re.IGNORECASE),
            re.compile(r'prototype\.', re.IGNORECASE),
            re.compile(r'\.constructor', re.IGNORECASE),
        ]

        # SQL injection patterns
        self._patterns['sql_injection'] = [
            re.compile(r'union\s+select', re.IGNORECASE),
            re.compile(r'drop\s+table', re.IGNORECASE),
            re.compile(r'delete\s+from', re.IGNORECASE),
            re.compile(r'insert\s+into', re.IGNORECASE),
            re.compile(r'update\s+set', re.IGNORECASE),
            re.compile(r'exec\s*\(', re.IGNORECASE),
            re.compile(r'execute\s*\(', re.IGNORECASE),
            re.compile(r'sp_executesql', re.IGNORECASE),
            re.compile(r'xp_cmdshell', re.IGNORECASE),
            re.compile(r'--\s*$', re.MULTILINE),
            re.compile(r'/\*.*?\*/', re.DOTALL),
            re.compile(r';.*--', re.IGNORECASE),
            re.compile(r"'\s*or\s*'", re.IGNORECASE),
            re.compile(r'"\s*or\s*"', re.IGNORECASE),
            re.compile(r"'\s*;\s*", re.IGNORECASE),
            re.compile(r'"\s*;\s*', re.IGNORECASE),
        ]

        # NoSQL injection patterns
        self._patterns['nosql_injection'] = [
            re.compile(r'\$where', re.IGNORECASE),
            re.compile(r'\$ne', re.IGNORECASE),
            re.compile(r'\$gt', re.IGNORECASE),
            re.compile(r'\$lt', re.IGNORECASE),
            re.compile(r'\$regex', re.IGNORECASE),
            re.compile(r'\$or', re.IGNORECASE),
            re.compile(r'\$and', re.IGNORECASE),
            re.compile(r'\$in', re.IGNORECASE),
            re.compile(r'\$nin', re.IGNORECASE),
            re.compile(r'function\s*\(', re.IGNORECASE),
            re.compile(r'this\s*\.', re.IGNORECASE),
        ]

        # OpenSearch/Elasticsearch specific patterns
        self._patterns['opensearch_injection'] = [
            re.compile(r'_search\s*\{', re.IGNORECASE),
            re.compile(r'_bulk\s*\{', re.IGNORECASE),
            re.compile(r'_delete_by_query', re.IGNORECASE),
            re.compile(r'_update_by_query', re.IGNORECASE),
            re.compile(r'script\s*:', re.IGNORECASE),
            re.compile(r'inline\s*:', re.IGNORECASE),
            re.compile(r'source\s*:', re.IGNORECASE),
            re.compile(r'params\s*:', re.IGNORECASE),
            re.compile(r'lang\s*:', re.IGNORECASE),
            re.compile(r'painless', re.IGNORECASE),
            re.compile(r'groovy', re.IGNORECASE),
            re.compile(r'expression', re.IGNORECASE),
        ]

        # Command injection patterns
        self._patterns['command_injection'] = [
            re.compile(r';\s*\w+', re.IGNORECASE),
            re.compile(r'\|\s*\w+', re.IGNORECASE),
            re.compile(r'&&\s*\w+', re.IGNORECASE),
            re.compile(r'\$\(', re.IGNORECASE),
            re.compile(r'`.*`', re.DOTALL),
            re.compile(r'>\s*/dev/', re.IGNORECASE),
            re.compile(r'<\s*/dev/', re.IGNORECASE),
            re.compile(r'/bin/', re.IGNORECASE),
            re.compile(r'/usr/bin/', re.IGNORECASE),
            re.compile(r'wget\s+', re.IGNORECASE),
            re.compile(r'curl\s+', re.IGNORECASE),
            re.compile(r'nc\s+', re.IGNORECASE),
            re.compile(r'netcat\s+', re.IGNORECASE),
        ]

        # Path traversal patterns
        self._patterns['path_traversal'] = [
            re.compile(r'\.\./', re.IGNORECASE),
            re.compile(r'\.\.\\', re.IGNORECASE),
            re.compile(r'/etc/', re.IGNORECASE),
            re.compile(r'/proc/', re.IGNORECASE),
            re.compile(r'/sys/', re.IGNORECASE),
            re.compile(r'/dev/', re.IGNORECASE),
            re.compile(r'/var/', re.IGNORECASE),
            re.compile(r'c:\\windows', re.IGNORECASE),
            re.compile(r'c:\\program', re.IGNORECASE),
            re.compile(r'%windir%', re.IGNORECASE),
            re.compile(r'%systemroot%', re.IGNORECASE),
        ]

        # LDAP injection patterns
        self._patterns['ldap_injection'] = [
            re.compile(r'\(\s*\|', re.IGNORECASE),
            re.compile(r'\(\s*&', re.IGNORECASE),
            re.compile(r'\*\s*\)', re.IGNORECASE),
            re.compile(r'=\s*\*', re.IGNORECASE),
            re.compile(r'\)\s*\(', re.IGNORECASE),
            re.compile(r'objectclass=', re.IGNORECASE),
            re.compile(r'cn=', re.IGNORECASE),
        ]

        # XXE patterns
        self._patterns['xxe_injection'] = [
            re.compile(r'<!ENTITY', re.IGNORECASE),
            re.compile(r'SYSTEM\s+', re.IGNORECASE),
            re.compile(r'PUBLIC\s+', re.IGNORECASE),
            re.compile(r'&\w+;', re.IGNORECASE),
            re.compile(r'<!DOCTYPE', re.IGNORECASE),
        ]

        # Template injection patterns
        self._patterns['template_injection'] = [
            re.compile(r'\{\{.*\}\}', re.DOTALL),
            re.compile(r'\{%.*%\}', re.DOTALL),
            re.compile(r'\$\{.*\}', re.DOTALL),
            re.compile(r'<%.*%>', re.DOTALL),
            re.compile(r'#\{.*\}', re.DOTALL),
        ]

        # Bot detection patterns
        self._patterns['bot_detection'] = [
            re.compile(r'bot', re.IGNORECASE),
            re.compile(r'crawl', re.IGNORECASE),
            re.compile(r'spider', re.IGNORECASE),
            re.compile(r'scrape', re.IGNORECASE),
            re.compile(r'fetch', re.IGNORECASE),
            re.compile(r'curl', re.IGNORECASE),
            re.compile(r'wget', re.IGNORECASE),
            re.compile(r'python', re.IGNORECASE),
            re.compile(r'java', re.IGNORECASE),
            re.compile(r'go-http', re.IGNORECASE),
            re.compile(r'automated', re.IGNORECASE),
            re.compile(r'scanner', re.IGNORECASE),
            re.compile(r'monitor', re.IGNORECASE),
        ]

        # HTML/XML patterns
        self._patterns['html_tags'] = re.compile(r'<[^>]*>', re.IGNORECASE)
        self._patterns['script_tags'] = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)

        # Email validation
        self._patterns['email'] = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

        # Field name validation
        self._patterns['safe_field_name'] = re.compile(r'^[a-zA-Z0-9._-]+$')

        # Special characters count
        self._patterns['special_chars'] = re.compile(r'[^\w\s-]')

        # Filename sanitization
        self._patterns['unsafe_filename_chars'] = re.compile(r'[^\w\-_\.]')

        # URL validation
        self._patterns['url_scheme'] = re.compile(r'^https?://', re.IGNORECASE)

        # JSON injection patterns
        self._patterns['json_injection'] = [
            re.compile(r'\{.*script.*\}', re.IGNORECASE | re.DOTALL),
            re.compile(r'\{.*source.*\}', re.IGNORECASE | re.DOTALL),
            re.compile(r'\{.*inline.*\}', re.IGNORECASE | re.DOTALL),
            re.compile(r'\{.*eval.*\}', re.IGNORECASE | re.DOTALL),
        ]

        # Credit card patterns
        self._patterns['credit_card'] = {
            'visa': re.compile(r'^4[0-9]{12}(?:[0-9]{3})?$'),
            'mastercard': re.compile(r'^5[1-5][0-9]{14}$'),
            'amex': re.compile(r'^3[47][0-9]{13}$'),
            'discover': re.compile(r'^6(?:011|5[0-9]{2})[0-9]{12}$'),
        }

    def check_patterns(self, text: str, pattern_group: str) -> bool:
        """Check if text matches any pattern in the specified group"""
        if not text or pattern_group not in self._patterns:
            return False

        patterns = self._patterns[pattern_group]
        if isinstance(patterns, list):
            return any(pattern.search(text) for pattern in patterns)
        elif isinstance(patterns, Pattern):
            return bool(patterns.search(text))
        else:
            return False

    def find_matches(self, text: str, pattern_group: str) -> List[str]:
        """Find all matches for patterns in the specified group"""
        if not text or pattern_group not in self._patterns:
            return []

        matches = []
        patterns = self._patterns[pattern_group]
        if isinstance(patterns, list):
            for pattern in patterns:
                matches.extend(pattern.findall(text))
        elif isinstance(patterns, Pattern):
            matches.extend(patterns.findall(text))

        return matches

    def get_pattern(self, pattern_name: str) -> Pattern:
        """Get a specific compiled pattern"""
        return self._patterns.get(pattern_name)

    def is_dangerous_string(self, text: str) -> bool:
        """Comprehensive check for dangerous string patterns"""
        if not text:
            return False

        # Check multiple pattern groups
        dangerous_groups = [
            'dangerous_strings',
            'sql_injection', 
            'nosql_injection',
            'command_injection',
            'path_traversal',
            'ldap_injection',
            'xxe_injection',
            'template_injection',
            'json_injection'
        ]

        return any(self.check_patterns(text, group) for group in dangerous_groups)

    def validate_field_name(self, field_name: str) -> bool:
        """Validate field name against safe patterns"""
        return bool(self._patterns['safe_field_name'].match(field_name))

    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        return bool(self._patterns['email'].match(email))

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename using compiled patterns"""
        if not filename:
            return ""

        # Remove path traversal attempts
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')

        # Keep only safe characters
        filename = self._patterns['unsafe_filename_chars'].sub('', filename)

        # Limit length
        return filename[:100]

    def count_special_chars(self, text: str) -> int:
        """Count special characters in text"""
        return len(self._patterns['special_chars'].findall(text))

    def is_bot_user_agent(self, user_agent: str) -> bool:
        """Check if user agent indicates bot behavior"""
        return self.check_patterns(user_agent, 'bot_detection')

    def validate_credit_card(self, number: str, card_type: str = None) -> bool:
        """Validate credit card number format"""
        if not number:
            return False

        # Remove spaces and hyphens
        number = re.sub(r'[\s-]', '', number)

        if card_type and card_type in self._patterns['credit_card']:
            return bool(self._patterns['credit_card'][card_type].match(number))

        # Check against all card types
        return any(pattern.match(number) for pattern in self._patterns['credit_card'].values())

# Global instance for efficient pattern reuse
security_patterns = SecurityPatterns()
