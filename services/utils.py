import re
import html
from urllib.parse import quote
from datetime import datetime, timedelta
import bleach

def truncate_description(text, limit=300):
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."

def fix_encoding(text):
    if isinstance(text, bytes):
        return text.decode('utf-8', errors='replace')
    try:
        return text.encode('latin1').decode('utf-8')
    except Exception:
        return text

def get_date_range_days(days_ago):
    nowutc = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    target_date = nowutc - timedelta(days=days_ago)
    return {'gte': target_date.isoformat()}

def sanitize_input(input_str, max_length=200, allow_basic_html=False):
    """
    Comprehensive input sanitization
    """
    if not input_str or not isinstance(input_str, str):
        return ""
    
    # Remove null bytes and control characters
    input_str = input_str.replace('\x00', '')
    input_str = ''.join(char for char in input_str if ord(char) >= 32 or char in '\t\n\r')
    
    # Normalize unicode
    import unicodedata
    input_str = unicodedata.normalize('NFKC', input_str)
    
    # Length limiting
    input_str = input_str[:max_length]
    
    if allow_basic_html:
        # Use bleach for HTML sanitization
        allowed_tags = ['b', 'i', 'em', 'strong']
        input_str = bleach.clean(input_str, tags=allowed_tags, strip=True)
    else:
        # Remove all HTML/XML tags
        input_str = re.sub(r'<[^>]*>', '', input_str)
    
    # Remove dangerous characters for SQL/NoSQL injection
    dangerous_chars = ['<', '>', '"', "'", '`', '\\', ';', '(', ')', '{', '}', '[', ']']
    for char in dangerous_chars:
        input_str = input_str.replace(char, '')
    
    # Remove script-related keywords (case insensitive)
    script_patterns = [
        r'javascript:', r'vbscript:', r'data:', r'file:', r'ftp:',
        r'on\w+\s*=', r'script', r'iframe', r'object', r'embed',
        r'expression\s*\(', r'url\s*\(', r'import\s+', r'@import'
    ]
    
    for pattern in script_patterns:
        input_str = re.sub(pattern, '', input_str, flags=re.IGNORECASE)
    
    # Trim whitespace
    input_str = input_str.strip()
    
    return input_str

def validate_search_query(query):
    """
    Validate search query with additional checks
    """
    if not query:
        return True, ""
    
    # Check for excessively long queries
    if len(query) > 200:
        return False, "Search query too long"
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'union\s+select', r'drop\s+table', r'delete\s+from',
        r'insert\s+into', r'update\s+set', r'exec\s*\(',
        r'<script', r'javascript:', r'vbscript:'
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return False, "Invalid characters in search query"
    
    return True, sanitize_input(query)

def validate_filter_values(values, allowed_values=None, max_items=50):
    """
    Validate filter values (countries, organizations, sources)
    """
    if not values:
        return []
    
    if len(values) > max_items:
        values = values[:max_items]
    
    sanitized = []
    for value in values:
        clean_value = sanitize_input(value, max_length=100)
        if clean_value and len(clean_value) >= 2:  # Minimum length check
            if allowed_values is None or clean_value in allowed_values:
                sanitized.append(clean_value)
    
    return sanitized