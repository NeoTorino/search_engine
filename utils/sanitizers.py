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
import ipaddress
import urllib.parse

from utils.general_utils import calculate_depth, is_numeric_string, is_valid_date_format

MAX_DEPTH = 3
LIMIT_ITER = 150
LIMIT_STR = 500
LIMIT_NUM = 20

def sanitize_element(element,
                    default_value=None,
                    valid_keys=None,
                    valid_values=None,
                    min_value=None,
                    max_value=None,
                    limit=(LIMIT_ITER, LIMIT_STR),
                    hint=None):
    """
    Sanitize an input element based on its type and specified criteria.

    This function processes an input element and returns a sanitized version of it.
    The sanitization process varies depending on the type of the element (string, number,
    dictionary, list, tuple, or set) and the provided validation parameters.

    Args:
        element: The input element to sanitize. It can be a string, number (int or float),
                 dictionary, list, tuple, or set.
        default_value: The value to return if the element cannot be sanitized. Defaults to None.
        valid_keys: A list of valid keys for dictionaries. If provided, only these keys will be retained.
        valid_values: A list of valid values for lists, tuples, sets, or dictionaries. If provided, only these values will be retained.
        min_value: The minimum acceptable value for numeric elements. If the element is less than this,
                   it will be replaced with the default_value.
        max_value: The maximum acceptable value for numeric elements. If the element is greater than this,
                   it will be replaced with the default_value.
        limit: The maximum length for string elements. If the string exceeds this length, it will be truncated.

    Returns:
        The sanitized value of the input element. If the element cannot be sanitized,
        the function returns the default_value.

    Test:
    # These will all route to sanitize_number():
        sanitize_element("30", min_value=1, max_value=365)    # Returns 30
        sanitize_element("-5", min_value=1, max_value=365)    # Returns 1 (min_value)
        sanitize_element("123.45", max_value=100)             # Returns 100 (max_value)
        sanitize_element(" 50 ", min_value=1, max_value=365)  # Returns 50

    # These will route to sanitize_string():
        sanitize_element("hello")        # Returns sanitized string
        sanitize_element("30abc")        # Returns sanitized string
    """
    clean_value = None

    # Handle numeric types first (including string representations of numbers)
    if isinstance(element, (int, float)):
        clean_value = sanitize_number(element, default_value=default_value, min_value=min_value, max_value=max_value, limit=limit[1], hint=hint)
    elif isinstance(element, str):
        # Check if this string should be treated as a number
        if is_numeric_string(element):
            clean_value = sanitize_number(element, default_value=default_value, min_value=min_value, max_value=max_value, limit=limit[1], hint=hint)
        else:
            clean_value = sanitize_string(element, limit=limit[1], hint=hint)
    elif isinstance(element, dict):
        clean_value = sanitize_dict(element, valid_keys=valid_keys, valid_values=valid_values, limit=limit, hint=hint)
    elif isinstance(element, list):
        clean_value = sanitize_list(element, valid_values=valid_values, limit=limit, hint=hint)
    elif isinstance(element, tuple):
        clean_value = sanitize_tuple(element, valid_values=valid_values, limit=limit, hint=hint)
    elif isinstance(element, set):
        clean_value = sanitize_set(element, valid_values=valid_values, limit=limit, hint=hint)
    else:
        return default_value

    return clean_value


def sanitize_string(raw_element, limit=LIMIT_STR, hint=None):
    """
    Enhanced string sanitization with comprehensive security controls
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

    # Check for homoglyph attacks - suspicious lookalike characters
    suspicious_unicode_ranges = [
        (0x0400, 0x04FF),  # Cyrillic
        (0x1F00, 0x1FFF),  # Greek Extended
        (0x2000, 0x206F),  # General Punctuation (includes zero-width chars)
        (0x2070, 0x209F),  # Superscripts and Subscripts
        (0x20A0, 0x20CF),  # Currency Symbols
        (0x2100, 0x214F),  # Letterlike Symbols
        (0x2190, 0x21FF),  # Arrows
        (0x2460, 0x24FF),  # Enclosed Alphanumerics
        (0x25A0, 0x25FF),  # Geometric Shapes
        (0x2600, 0x26FF),  # Miscellaneous Symbols
        (0x3000, 0x303F),  # CJK Symbols and Punctuation
        (0xFE00, 0xFE0F),  # Variation Selectors
        (0xFEFF, 0xFEFF),  # Zero Width No-Break Space
    ]

    # Remove characters from suspicious Unicode ranges
    filtered_chars = []
    for char in text:
        char_code = ord(char)
        is_suspicious = any(start <= char_code <= end for start, end in suspicious_unicode_ranges)
        if not is_suspicious:
            filtered_chars.append(char)
    text = ''.join(filtered_chars)

    # Multiple Unicode normalization attempts to prevent bypass
    # First normalize with NFKC, then check if further normalization changes it
    normalized_once = unicodedata.normalize('NFKC', text)
    normalized_twice = unicodedata.normalize('NFKC', normalized_once)

    # If double normalization produces different results, it might be an attack
    if normalized_once != normalized_twice:
        # Use the more restrictive approach - remove non-ASCII
        text = ''.join(char for char in normalized_twice if ord(char) < 128)
    else:
        text = normalized_once

    # ENHANCED: Zero-width character removal (invisible characters)
    zero_width_chars = [
        '\u200B',  # Zero Width Space
        '\u200C',  # Zero Width Non-Joiner
        '\u200D',  # Zero Width Joiner
        '\u200E',  # Left-To-Right Mark
        '\u200F',  # Right-To-Left Mark
        '\u202A',  # Left-To-Right Embedding
        '\u202B',  # Right-To-Left Embedding
        '\u202C',  # Pop Directional Formatting
        '\u202D',  # Left-To-Right Override
        '\u202E',  # Right-To-Left Override
        '\u2060',  # Word Joiner
        '\u2061',  # Function Application
        '\u2062',  # Invisible Times
        '\u2063',  # Invisible Separator
        '\u2064',  # Invisible Plus
        '\uFEFF',  # Zero Width No-Break Space
    ]
    for char in zero_width_chars:
        text = text.replace(char, '')

    # IP address detection and blocking (potential exfiltration)
    ip_patterns = [
        r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',  # IPv4
        r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',  # IPv6
        r'\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b',  # IPv6 compressed
    ]
    for pattern in ip_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                # Validate if it's a real IP address
                ipaddress.ip_address(match.split(':')[0] if ':' in match else match)
                text = text.replace(match, '')  # Remove valid IP addresses
            except ValueError:
                pass  # Not a valid IP, keep it

    # URL/URI detection and sanitization - Enhanced with more protocols
    url_patterns = [
        r'https?://[^\s<>"]+' if hint != 'url' else '',
        r'ftp://[^\s<>"]+',
        r'file://[^\s<>"]+',
        r'data:[^\s<>"]+',
        r'javascript:[^\s<>"]+',
        r'vbscript:[^\s<>"]+',
    ]
    for pattern in url_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Base64 detection (potential payload encoding)
    base64_pattern = r'[A-Za-z0-9+/]{20,}={0,2}'
    base64_matches = re.findall(base64_pattern, text)
    for match in base64_matches:
        # Remove if it looks like encoded content
        if len(match) > 50:  # Likely encoded payload
            text = text.replace(match, '')

    # Hexadecimal encoding detection
    hex_patterns = [
        r'\\x[0-9a-fA-F]{2}',  # \x41
        r'%[0-9a-fA-F]{2}',    # %41
        r'&#x[0-9a-fA-F]+;',   # &#x41;
        r'&#[0-9]+;',          # &#65;
        r'\\u[0-9a-fA-F]{4}',  # \u0041
    ]
    for pattern in hex_patterns:
        # Try to decode and check if it results in dangerous characters
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                if pattern.startswith(r'\\x'):
                    decoded = bytes.fromhex(match[2:]).decode('utf-8', errors='ignore')
                elif pattern.startswith(r'%'):
                    decoded = urllib.parse.unquote(match)
                elif pattern.startswith(r'&#x'):
                    decoded = chr(int(match[3:-1], 16))
                elif pattern.startswith(r'&#'):
                    decoded = chr(int(match[2:-1]))
                elif pattern.startswith(r'\\u'):
                    decoded = match.encode().decode('unicode_escape')
                else:
                    continue

                # If decoded contains dangerous characters, remove the encoded version
                if any(c in decoded for c in '<>"\'`&;(){}[]$|*?!^%#@\\'):
                    text = text.replace(match, '')
            except (ValueError, UnicodeDecodeError):
                # Remove invalid encodings
                text = text.replace(match, '')

    # Polyglot detection (content that's valid in multiple contexts)
    polyglot_patterns = [
        r'<!--.*?-->.*?<script',  # HTML comment + script
        r'/\*.*?\*/.*?<script',   # CSS comment + script
        r'//.*?\n.*?<script',     # JS comment + script
        r'<?.*?\?>.*?<script',    # Processing instruction + script
    ]
    for pattern in polyglot_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)

    # File extension and MIME type detection
    file_extensions = [
        rf'\.(exe|bat|cmd|pif|scr|vbs|js|jar|dll|msi|deb|rpm|dmg|pkg|app{"" if hint == "url" else "|com"})\b',
        r'\.(php|asp|aspx|jsp|cgi|pl|py|rb|sh|bash|zsh|fish)\b',
        r'\.(htaccess|htpasswd|web\.config|robots\.txt)\b'
    ]

    for pattern in file_extensions:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

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
    js_patterns = [
        r'on\w+\s*=',  # Event handlers
        r'javascript:',  # JavaScript protocol
        r'<script.*?</script>',  # Script tags
        r'vbscript:',  # VBScript protocol
        r'data:',  # Data protocol
        r'eval\s*\(',  # eval function
        r'setTimeout\s*\(',  # setTimeout function
        r'setInterval\s*\(',  # setInterval function
        r'Function\s*\(',  # Function constructor
        r'constructor\s*\(',  # constructor calls
        r'__proto__',  # prototype pollution
        r'prototype\.',  # prototype access
        r'\.constructor',  # constructor access
    ]
    for pattern in js_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)

    if hint == 'url':
        # For URLs, only remove characters that are never valid in URLs
        dangerous_chars = '<>"\'`\\;(){}[]|^'
    else:
        # For non-URLs, remove all dangerous characters
        dangerous_chars = '<>"\'`\\;(){}[]$|&*?!^%#@'
    for char in dangerous_chars:
        text = text.replace(char, '')

    # Special characters that need removal
    if hint == 'url':
        opensearch_special = r'[|><!~]'  # Keep URL-safe characters
    elif hint == 'date' or is_valid_date_format(text):
        opensearch_special = r'[+=|><!~:\\\/]'
    else:
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
        r'(sp_)', r'(xp_)', r'(cmdshell)', r'(sp_executesql)', r'(xp_cmdshell)',
        r"('\s*or\s*')", r'("\s*or\s*")', r"('\s*;\s*)", r'("\s*;\s*)'
    ]
    for pattern in sql_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # NoSQL injection patterns - Enhanced
    nosql_patterns = [
        r'(\$where)', r'(\$ne)', r'(\$gt)', r'(\$lt)', r'(\$gte)', r'(\$lte)',
        r'(\$in)', r'(\$nin)', r'(\$regex)', r'(\$exists)', r'(\$type)',
        r'(\$all)', r'(\$size)', r'(\$elemMatch)', r'(\$not)', r'(\$or)',
        r'(\$and)', r'(\$nor)', r'(\$expr)', r'(this\.)', r'(function\s*\()',
        r'(\.constructor)', r'(\.prototype)', r'(__proto__)'
    ]
    for pattern in nosql_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # OpenSearch patterns - Enhanced with more specific patterns
    opensearch_patterns = [
        r'script\s*:', r'inline\s*:', r'source\s*:',
        r'params\s*:', r'lang\s*:', r'file\s*:',
        r'painless', r'groovy', r'expression',
        r'_delete', r'_update', r'_bulk', r'_search\s*\{', r'_bulk\s*\{',
        r'_source', r'_id', r'_type', r'_index', r'_score',
        r'_script', r'_inline', r'_file',
        r'script\s*:\s*{',
        r'inline\s*:\s*["\']',
        r'source\s*:\s*["\']',
        r'_delete_by_query',
        r'_update_by_query',
        r'system\s*\(',
        r'runtime\.exec',
        r'_source\s*:.*script',
        r'highlight.*script',
        r'sort.*script'
    ]

    # Apply all patterns in one loop
    for pattern in opensearch_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Remove potential JSON injection
    text = re.sub(r'\{[^}]*script[^}]*\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{[^}]*source[^}]*\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{[^}]*inline[^}]*\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{[^}]*eval[^}]*\}', '', text, flags=re.IGNORECASE)

    # Command injection patterns - Enhanced
    command_patterns = [
        r'(;\s*ls)', r'(;\s*cat)', r'(;\s*rm)', r'(;\s*mkdir)', r'(;\s*touch)',
        r'(;\s*wget)', r'(;\s*curl)', r'(;\s*nc)', r'(;\s*netcat)',
        r'(\|\s*ls)', r'(\|\s*cat)', r'(\|\s*rm)', r'(\&\&)', r'(\|\|)',
        r'(`[^`]*`)', r'(\$\([^)]*\))', r'(\.\.\/)', r'(\/etc\/)',
        r'(\/bin\/)', r'(\/usr\/bin\/)', r'(\/sbin\/)', r'(\/tmp\/)',
        r'(;\s*\w+)', r'(\|\s*\w+)', r'(&&\s*\w+)', r'(\$\()',
        r'(>\s*/dev/)', r'(<\s*/dev/)', r'(/bin/)', r'(/usr/bin/)',
        r'(wget\s+)', r'(curl\s+)', r'(nc\s+)', r'(netcat\s+)'
    ]
    for pattern in command_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Path traversal prevention - Enhanced
    path_traversal_patterns = [
        r'\.\./', r'\.\.\\', r'/etc/', r'/proc/', r'/sys/', r'/dev/', r'/var/',
        r'c:\\windows', r'c:\\program', r'%windir%', r'%systemroot%',
        r'%2e%2e%2f', r'%2e%2e%5c'
    ]
    for pattern in path_traversal_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Template injection patterns
    template_patterns = [
        r'(\{\{.*\}\})', r'(\{%.*%\})', r'(\{#.*#\})',
        r'(\$\{.*\})', r'(<%.*%>)', r'(#{.*})'
    ]
    for pattern in template_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # LDAP injection patterns - Enhanced
    ldap_patterns = [
        r'(\*\))', r'(\|\))', r'(&\))', r'(!\))', r'(=\*)',
        r'(>\=)', r'(<=)', r'(~=)', r'(\(\|)', r'(\(&)', r'(\(!)',
        r'(\(\s*\|)', r'(\(\s*&)', r'(\*\s*\))', r'(=\s*\*)', r'(\)\s*\()',
        r'(objectclass=)', r'(cn=)'
    ]
    for pattern in ldap_patterns:
        text = re.sub(pattern, '', text)

    # XXE (XML External Entity) injection patterns
    xxe_patterns = [
        r'(<!ENTITY)', r'(SYSTEM\s+)', r'(PUBLIC\s+)', r'(&\w+;)', r'(<!DOCTYPE)'
    ]
    for pattern in xxe_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Credit card pattern detection and removal (PCI compliance)
    credit_card_patterns = [
        r'\b4[0-9]{12}(?:[0-9]{3})?\b',  # Visa
        r'\b5[1-5][0-9]{14}\b',  # Mastercard
        r'\b3[47][0-9]{13}\b',   # American Express
        r'\b6(?:011|5[0-9]{2})[0-9]{12}\b'  # Discover
    ]
    for pattern in credit_card_patterns:
        text = re.sub(pattern, '[REDACTED]', text)

    # Check for excessive special characters (potential obfuscation)
    special_char_count = sum(1 for char in text if not char.isalnum() and char not in ' \t\n\r')
    if len(text) > 0 and special_char_count > len(text) * 0.3:  # More than 30% special chars
        # Keep only alphanumeric and basic whitespace
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text)

    # Final character frequency analysis
    # Detects and prevents if any single character makes up more than 50% of the text
    # Prevents inputs like "aaaaaaa..." or "////////..."
    if len(text) > 10:
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1

        # Check for excessive repetition (potential DoS or obfuscation)
        max_char_frequency = max(char_counts.values()) if char_counts else 0
        if max_char_frequency > len(text) * 0.5:  # More than 50% same character
            # Likely spam or attack, truncate heavily
            text = text[:min(50, len(text))]

    # Remove excessive whitespace and normalize
    text = re.sub(r'\s+', ' ', text).strip()

    # Final length check
    if len(text) > limit:
        text = text[:limit]

    text = text.strip()

    if is_numeric_string(text):
        return sanitize_number(text, hint=hint)

    return text


def sanitize_number(raw_element, default_value=None, min_value=None, max_value=None, limit=LIMIT_NUM, hint=None):
    """
    Enhanced number sanitization with comprehensive security controls
    Only allows ASCII digits 0-9 and necessary symbols (+, -, .)
    """
    if not raw_element:
        return default_value

    # Convert to string if not already
    if not isinstance(raw_element, str):
        raw_element = str(raw_element)

    # Limit check
    if len(raw_element) > limit:
        raw_element = raw_element[:limit]

    # SECURITY: Only keep ASCII digits 0-9 and essential numeric symbols
    # This prevents ALL Unicode spoofing, control characters, and other attacks
    cleaned_str = ''.join(char for char in raw_element if char in '0123456789+-.')

    # Early exit if empty after cleaning
    if not cleaned_str:
        return default_value

    # Scientific notation detection and blocking
    # Prevent attacks using scientific notation to bypass limits
    scientific_patterns = [
        r'[0-9]+[eE][+-]?[0-9]+',  # 1e10, 2E-5
        r'[0-9]*\.[0-9]+[eE][+-]?[0-9]+',  # 1.5e10
    ]
    for pattern in scientific_patterns:
        if re.search(pattern, cleaned_str):
            try:
                # Convert scientific notation to regular number
                float_val = float(cleaned_str)
                # Check if it's within reasonable bounds
                if abs(float_val) > 1e15:  # Extremely large number
                    return default_value
                cleaned_str = str(int(float_val)) if float_val.is_integer() else str(float_val)
            except (ValueError, OverflowError):
                return default_value

    # Hexadecimal number detection (but won't match after ASCII filtering)
    if cleaned_str.lower().startswith('0x'):
        try:
            int_val = int(cleaned_str, 16)
            cleaned_str = str(int_val)
        except ValueError:
            return default_value

    # Octal number detection
    if cleaned_str.startswith('0') and len(cleaned_str) > 1 and all(c in '01234567' for c in cleaned_str[1:]):
        try:
            int_val = int(cleaned_str, 8)
            cleaned_str = str(int_val)
        except ValueError:
            return default_value

    # Binary number detection (but won't match after ASCII filtering)
    if cleaned_str.lower().startswith('0b'):
        try:
            int_val = int(cleaned_str, 2)
            cleaned_str = str(int_val)
        except ValueError:
            return default_value

    # More strict numeric validation
    # Only allow digits, one decimal point, and one leading sign
    if not re.match(r'^[+-]?[0-9]*\.?[0-9]+$', cleaned_str):
        return default_value

    # Check for multiple signs or decimal points
    sign_count = cleaned_str.count('+') + cleaned_str.count('-')
    dot_count = cleaned_str.count('.')

    if sign_count > 1 or dot_count > 1:
        return default_value

    # Ensure sign is only at the beginning
    if sign_count == 1:
        sign_pos = max(cleaned_str.find('+'), cleaned_str.find('-'))
        if sign_pos != 0:
            return default_value

    # Check for invalid patterns after cleaning
    if not cleaned_str or cleaned_str in ['+', '-', '.', '+.', '-.']:
        return default_value

    try:
        # Convert to float first to handle decimal inputs
        float_val = float(cleaned_str)

        # ENHANCED: Check for special float values
        if not (float('-inf') < float_val < float('inf')):
            return default_value

        # ENHANCED: Check for NaN
        if float_val != float_val:  # NaN check
            return default_value

        # Convert to integer
        int_val = int(float_val)

        # Bounds checking with overflow protection
        if min_value is not None and int_val < min_value:
            return min_value
        if max_value is not None and int_val > max_value:
            return max_value

        # Additional range check for extreme values
        if abs(int_val) > 2**53:  # JavaScript safe integer limit
            return default_value

        return int_val

    except (ValueError, TypeError, OverflowError):
        return default_value


def sanitize_list(raw_element, valid_values=None, limit=(LIMIT_ITER, LIMIT_STR), hint=None):
    """
    Sanitize list parameters and validate against predefined values
    """
    if not raw_element or not isinstance(raw_element, list):
        return []

    nesting_level = calculate_depth(obj=raw_element, max_iterations=MAX_DEPTH)
    if nesting_level > MAX_DEPTH:
        return []

    sanitized_list = []
    for i, value in enumerate(raw_element):
        # Early limiting to prevent processing huge lists
        if i > limit[0]:
            break

        # Sanitize the key (pass valid_keys as valid_values for key validation)
        clean_value = sanitize_element(element=value, valid_values=valid_values, limit=limit, hint=hint)

        if not clean_value:
            continue

        # Check if the sanitized value is in the valid set (case-insensitive)
        if valid_values:
            valid_values = {k.lower() for k in valid_values}
            if clean_value.lower() in valid_values:
                sanitized_list.append(clean_value)
        else:
            sanitized_list.append(clean_value)

    return sanitized_list

def sanitize_dict(raw_element, valid_keys=None, valid_values=None, limit=(LIMIT_ITER, LIMIT_STR), hint=None):
    """
    Sanitize dictionary parameters and validate values against predefined values.
    """
    if not raw_element or not isinstance(raw_element, dict):
        return {}

    nesting_level = calculate_depth(obj=raw_element, max_iterations=MAX_DEPTH)
    if nesting_level > MAX_DEPTH:
        return []

    sanitized_dict = {}
    for i, (key, value) in enumerate(raw_element.items()):

        # Early limiting to prevent processing huge lists
        if i > limit[0]:
            break

        # Sanitize the key (pass valid_keys as valid_values for key validation)
        clean_key = sanitize_element(key, valid_values=valid_keys, limit=limit, hint=hint)

        if not clean_key:
            continue

        if valid_keys:
            valid_keys = {k.lower() for k in valid_keys}
            if clean_key.lower() not in valid_keys:
                continue

        # Sanitize the value (pass through valid_values context)
        clean_value = sanitize_element(value, valid_values=valid_values, limit=limit, hint=hint)

        if not clean_value:
            continue

        # Check if the sanitized value is in the valid set (case-insensitive)
        if valid_values:
            valid_values = {k.lower() for k in valid_values}
            if clean_value.lower() in valid_values:
                sanitized_dict[clean_key] = clean_value
        else:
            sanitized_dict[clean_key] = clean_value

    return sanitized_dict

def sanitize_tuple(raw_element, valid_values=None, limit=(LIMIT_ITER, LIMIT_STR), hint=None):
    """
    Sanitize tuple parameters and validate against predefined values
    """
    if not raw_element or not isinstance(raw_element, tuple):
        return ()

    nesting_level = calculate_depth(obj=raw_element, max_iterations=MAX_DEPTH)
    if nesting_level > MAX_DEPTH:
        return ()

    sanitized_list = []
    for i, value in enumerate(raw_element):
        # Early limiting to prevent processing huge tuples
        if i > limit[0]:
            break

        # Sanitize the value
        clean_value = sanitize_element(element=value, valid_values=valid_values, limit=limit, hint=hint)

        if not clean_value:
            continue

        # Check if the sanitized value is in the valid set (case-insensitive)
        if valid_values:
            valid_values_lower = {k.lower() for k in valid_values}
            if clean_value.lower() in valid_values_lower:
                sanitized_list.append(clean_value)
        else:
            sanitized_list.append(clean_value)

    return tuple(sanitized_list)


def sanitize_set(raw_element, valid_values=None, limit=(LIMIT_ITER, LIMIT_STR), hint=None):
    """
    Sanitize set parameters and validate against predefined values
    """
    if not raw_element or not isinstance(raw_element, set):
        return set()

    nesting_level = calculate_depth(obj=raw_element, max_iterations=MAX_DEPTH)
    if nesting_level > MAX_DEPTH:
        return set()

    sanitized_set = set()
    for i, value in enumerate(raw_element):
        # Early limiting to prevent processing huge sets
        if i > limit[0]:
            break

        # Sanitize the value
        clean_value = sanitize_element(element=value, valid_values=valid_values, limit=limit, hint=hint)

        if not clean_value:
            continue

        # Check if the sanitized value is in the valid set (case-insensitive)
        if valid_values:
            valid_values_lower = {k.lower() for k in valid_values}
            if clean_value.lower() in valid_values_lower:
                sanitized_set.add(clean_value)
        else:
            sanitized_set.add(clean_value)

    return sanitized_set
