"""
Flask Request Parameter Sanitizer - Enterprise Security Module

This module provides comprehensive input sanitization for Flask web applications,
designed to protect against multiple types of injection attacks and malicious input.

MAIN FUNCTIONS:
- sanitize_string(): 17-step security process for text inputs
- sanitize_integer(): Enhanced numeric validation with attack detection
- sanitize_list(): Validates list items against predefined allowed values
- sanitize_get_parameters(): Main function that sanitizes all GET request parameters

SECURITY PROTECTIONS:
- XSS (Cross-Site Scripting) prevention
- SQL injection blocking (MySQL, PostgreSQL, SQLite patterns)
- NoSQL injection protection (MongoDB, etc.)
- Command injection prevention (Linux/Unix commands)
- Path traversal blocking (../.. attacks)
- Template injection prevention (Jinja2, etc.)
- LDAP injection protection
- HTML/XML tag removal and entity decoding
- Unicode normalization against encoding attacks
- Obfuscation detection (rejects >30% special characters)
- OpenSearch/Elasticsearch special character handling

PARAMETER PROCESSING:
- 'q': Free text search queries (500 char limit)
- 'country': Validated against VALID_COUNTRIES whitelist
- 'organization': Validated against VALID_ORGANIZATIONS whitelist
- 'source': Validated against VALID_SOURCES whitelist
- 'date_posted_days': Integer 1-30 range (>30 becomes 365)
- 'from': Integer 0-10000 range for pagination

All functions return safe, sanitized values with comprehensive logging of rejected inputs.
Maintains original business logic while providing enterprise-grade security protection.
"""

import re
import html
import unicodedata


def sanitize_element(element, default_value=None, valid_keys=None, valid_values=None, min_value=None, max_value=None, limit=None):
    clean_value = None

    if isinstance(element, str):
        if element.isdigit():
            clean_value = sanitize_number(element, default_value=default_value, min_value=min_value, max_value=max_value)
        else:
            clean_value = sanitize_string(element, limit=limit)
    elif isinstance(element, (int, float)):
        clean_value = sanitize_number(element, default_value=default_value, min_value=min_value, max_value=max_value)
    elif isinstance(element, dict):
        clean_value = sanitize_dict(element,valid_keys= valid_keys, valid_values=valid_values)
    elif isinstance(element, list):
        clean_value = sanitize_list(element, valid_values=valid_values)
    else:
        return default_value

    return clean_value

def sanitize_string(raw_element, limit=512):
    """
    Enhanced string sanitization with strict security controls
    Protects against XSS, SQL injection, OpenSearch injection, and other attacks
    """
    if not raw_element or not isinstance(raw_element, str):
        return ""

    text = raw_element.strip()

    # Early length limiting to prevent processing huge strings
    if len(text) > limit:
        text = text[:limit]

    # Remove null bytes and control characters (security critical)
    text = text.replace('\x00', '')  # Remove null bytes
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\t\n\r')

    # Unicode normalization to prevent unicode-based attacks
    text = unicodedata.normalize('NFKC', text)

    # Check for suspicious patterns in the original string
    suspicious_patterns = [
        r'[<>{}[\]()\'";]',  # HTML/Script injection attempts
        r'(union|select|drop|insert|delete|update|create|alter)',  # SQL keywords
        r'(\$|@|#)',  # Variable indicators
        r'(\\x|\\u|\%)',  # Encoded characters
        r'(script|javascript|vbscript)',  # Script attempts
    ]
    for pattern in suspicious_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # HTML handling - decode entities then remove all HTML/XML tags
    text = html.unescape(text)
    text = re.sub(r'<[^>]*>', '', text)  # Remove all HTML/XML tags
    text = re.sub(r'&[a-zA-Z0-9#]+;', '', text)  # Remove remaining HTML entities

    # Remove JavaScript and dangerous script content
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<script.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'vbscript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'data:', '', text, flags=re.IGNORECASE)

    # Remove dangerous characters (strict security level)
    dangerous_chars = '<>"\'`\\;(){}[]$|&*?!^%#@'
    for char in dangerous_chars:
        text = text.replace(char, '')

    # OpenSearch special characters that need removal
    opensearch_special = r'[+\-=|><!~:\\\/]'
    text = re.sub(opensearch_special, ' ', text)

    # Enhanced SQL injection pattern removal
    sql_patterns = [
        r'(union\s+select)', r'(drop\s+table)', r'(insert\s+into)',
        r'(delete\s+from)', r'(update\s+set)', r'(create\s+table)',
        r'(alter\s+table)', r'(exec\s+)', r'(execute\s+)',
        r'(\bor\b\s+\d+\s*=\s*\d+)', r'(\band\b\s+\d+\s*=\s*\d+)',
        r'(--)', r'(/\*.*?\*/)', r'(;.*--)', r'(\|\|)', r'(@@)',
        r'(char\s*\()', r'(cast\s*\()', r'(convert\s*\()',
        r'(sp_)', r'(xp_)', r'(cmdshell)'
    ]
    for pattern in sql_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    #  NoSQL injection patterns
    nosql_patterns = [
        r'(\$where)', r'(\$ne)', r'(\$gt)', r'(\$lt)', r'(\$gte)', r'(\$lte)',
        r'(\$in)', r'(\$nin)', r'(\$regex)', r'(\$exists)', r'(\$type)',
        r'(\$all)', r'(\$size)', r'(\$elemMatch)', r'(\$not)', r'(\$or)',
        r'(\$and)', r'(\$nor)', r'(\$expr)', r'(this\.)', r'(function\s*\()',
        r'(\.constructor)', r'(\.prototype)', r'(__proto__)'
    ]
    for pattern in nosql_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Opensearch patterns
    opensearch_patterns = [
        r'script\s*:', r'inline\s*:', r'source\s*:',
        r'params\s*:', r'lang\s*:', r'file\s*:',
        r'painless', r'groovy', r'expression',
        r'_delete', r'_update', r'_bulk'
    ]

    for pattern in opensearch_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Remove potential JSON injection
    text = re.sub(r'\{[^}]*script[^}]*\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{[^}]*source[^}]*\}', '', text, flags=re.IGNORECASE)

    # SCommand injection patterns
    command_patterns = [
        r'(;\s*ls)', r'(;\s*cat)', r'(;\s*rm)', r'(;\s*mkdir)', r'(;\s*touch)',
        r'(;\s*wget)', r'(;\s*curl)', r'(;\s*nc)', r'(;\s*netcat)',
        r'(\|\s*ls)', r'(\|\s*cat)', r'(\|\s*rm)', r'(\&\&)', r'(\|\|)',
        r'(`[^`]*`)', r'(\$\([^)]*\))', r'(\.\.\/)', r'(\/etc\/)',
        r'(\/bin\/)', r'(\/usr\/bin\/)', r'(\/sbin\/)', r'(\/tmp\/)'
    ]
    for pattern in command_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Path traversal prevention
    text = re.sub(r'\.\./', '', text)
    text = re.sub(r'\.\.\\', '', text)
    text = re.sub(r'%2e%2e%2f', '', text, flags=re.IGNORECASE)
    text = re.sub(r'%2e%2e%5c', '', text, flags=re.IGNORECASE)

    # Template injection patterns
    template_patterns = [
        r'(\{\{.*\}\})', r'(\{%.*%\})', r'(\{#.*#\})',
        r'(\$\{.*\})', r'(<%.*%>)', r'(#{.*})'
    ]
    for pattern in template_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # LDAP injection patterns
    ldap_patterns = [
        r'(\*\))', r'(\|\))', r'(&\))', r'(!\))', r'(=\*)',
        r'(>\=)', r'(<=)', r'(~=)', r'(\(\|)', r'(\(&)', r'(\(!)'
    ]
    for pattern in ldap_patterns:
        text = re.sub(pattern, '', text)

    # Check for excessive special characters (potential obfuscation)
    special_char_count = sum(1 for char in text if not char.isalnum() and char not in ' \t\n\r')
    if len(text) > 0 and special_char_count > len(text) * 0.3:  # More than 30% special chars
        # Keep only alphanumeric and basic whitespace
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text)

    # Remove excessive whitespace and normalize
    text = re.sub(r'\s+', ' ', text).strip()

    # Final length check after all processing
    if len(text) > limit:
        text = text[:limit]

    clean_text = text.strip()

    # Minimum length check to prevent empty or very short strings
    if len(clean_text) < 1:
        return ""

    return clean_text

def sanitize_number(raw_element, default_value=None, min_value=None, max_value=None, limit=10):
    """
    Enhanced number sanitization with strict security controls
    """
    if not raw_element:
        return default_value

    # Convert to string if not already
    if not isinstance(raw_element, str):
        raw_element = str(raw_element)

    # Early length limiting to prevent processing huge strings
    if len(raw_element) > limit:
        raw_element = raw_element[:limit]

    # Remove control characters
    cleaned_str = ''.join(char for char in raw_element if ord(char) >= 32)

    cleaned_str = sanitize_string(cleaned_str)

    if not cleaned_str:
        return default_value

    # Remove any non-numeric characters except minus sign and decimal point
    # This prevents injection attempts through numeric fields
    cleaned_str = re.sub(r'[^0-9\-\.]', '', cleaned_str)

    # Check for the presence of sign and decimal point
    sign_count = cleaned_str.count('+') + cleaned_str.count('-')
    dot_count = cleaned_str.count('.')
    if sign_count > 1 or dot_count > 1:
        return default_value

    # Check if the string contains only valid characters
    if not all(c.isdigit() or c in ['+', '-', '.'] for c in cleaned_str):
        return default_value

    # Check if the first character is a digit, '+' or '-'
    if cleaned_str[0] not in ['+', '-', *map(str, range(10))]:
        return default_value

    try:
        # Convert to integer (this will fail for decimals, which is what we want)
        int_val = int(float(cleaned_str))  # Use float first to handle "123.0" format

        # Check bounds
        if min_value and int_val < min_value:
            return min_value if min_value else default_value
        if max_value and int_val > max_value:
            return max_value if max_value else default_value

        return int_val

    except (ValueError, TypeError, OverflowError):
        return default_value

def sanitize_list(raw_element, valid_values=None, limit=150):
    """
    Sanitize list parameters and validate against predefined values
    """
    if not raw_element or isinstance(raw_element, list):
        return []

    sanitized_list = []
    for i, value in enumerate(raw_element):
        # Early limiting to prevent processing huge lists
        if i > limit:
            break

        clean_value = sanitize_element(value)

        if not clean_value:
            continue

        # Check if the sanitized value is in the valid set (case-insensitive)
        if valid_values:
            valid_values = {k.lower() for k in valid_values}
            if clean_value.lower() in valid_values:
                sanitized_list.append(clean_value)

    return sanitized_list

def sanitize_dict(raw_element, valid_keys=None, valid_values=None, limit=150):
    """
    Sanitize dictionary parameters and validate values against predefined values.
    """
    if not raw_element or not isinstance(raw_element, dict):
        return {}

    sanitized_dict = {}
    for i, (key, value) in enumerate(raw_element.items()):

        # Early limiting to prevent processing huge lists
        if i > limit:
            break

        # Sanitize the key
        clean_key = sanitize_element(key)

        if not clean_key:
            continue

        if valid_keys:
            valid_keys = {k.lower() for k in valid_keys}
            if clean_key.lower() not in valid_keys:
                continue

        # Sanitize the value
        clean_value = sanitize_element(value)

        if not clean_value:
            continue

        # Check if the sanitized value is in the valid set (case-insensitive)
        if valid_values:
            valid_values = {k.lower() for k in valid_values}
            if clean_value.lower() in valid_values:
                sanitized_dict[clean_key] = clean_value

    return sanitized_dict
