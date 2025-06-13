from datetime import datetime, timedelta

def truncate_description(text, limit=300):
    """
    Truncate text description to specified limit, breaking at word boundaries
    """
    if not text or len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."

def fix_encoding(text):
    """
    Fix common encoding issues in text
    """
    if isinstance(text, bytes):
        return text.decode('utf-8', errors='replace')
    try:
        # Handle latin1 to utf-8 conversion
        return text.encode('latin1').decode('utf-8')
    except Exception:
        return text

def get_date_range_days(days):
    """
    Get date range for filtering jobs based on number of days
    Returns dict with start and end datetime objects
    """
    if days <= 0:
        return None

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    return {
        'start': start_date,
        'end': end_date
    }

def format_date_for_display(date_obj, format_str="%Y-%m-%d"):
    """
    Format datetime object for display
    """
    if not date_obj:
        return ""

    if isinstance(date_obj, str):
        try:
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        except ValueError:
            return date_obj

    return date_obj.strftime(format_str)

def parse_date_string(date_str):
    """
    Parse date string in various formats to datetime object
    """
    if not date_str:
        return None

    # Common date formats to try
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y",
        "%d/%m/%Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None

def calculate_time_ago(date_obj):
    """
    Calculate human-readable time difference from now
    """
    if not date_obj:
        return "Unknown"

    if isinstance(date_obj, str):
        date_obj = parse_date_string(date_obj)
        if not date_obj:
            return "Unknown"

    now = datetime.utcnow()
    diff = now - date_obj

    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

def clean_text(text, remove_extra_spaces=True):
    """
    Clean text by removing extra whitespace and normalizing
    """
    if not text:
        return ""

    # Remove extra whitespace
    if remove_extra_spaces:
        text = ' '.join(text.split())

    # Strip leading/trailing whitespace
    text = text.strip()

    return text

def extract_domain_from_url(url):
    """
    Extract domain name from URL
    """
    if not url:
        return ""

    # Simple domain extraction
    if url.startswith(('http://', 'https://')):
        url = url.split('//', 1)[1]

    domain = url.split('/')[0]

    # Remove www prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]

    return domain

def pluralize(count, singular, plural=None):
    """
    Return singular or plural form based on count
    """
    if count == 1:
        return singular

    if plural is None:
        plural = singular + 's'

    return plural

def format_number(number):
    """
    Format number with thousands separators
    """
    if not isinstance(number, (int, float)):
        return str(number)

    return f"{number:,}"

def slugify(text, max_length=50):
    """
    Convert text to URL-friendly slug
    """
    if not text:
        return ""

    import re

    # Convert to lowercase and replace spaces with hyphens
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug)

    # Remove leading/trailing hyphens
    slug = slug.strip('-')

    # Limit length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('-')

    return slug

def merge_dicts(*dicts):
    """
    Merge multiple dictionaries, with later ones taking precedence
    """
    result = {}
    for d in dicts:
        if isinstance(d, dict):
            result.update(d)
    return result

def safe_int(value, default=0):
    """
    Safely convert value to integer
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    """
    Safely convert value to float
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def get_nested_value(data, keys, default=None):
    """
    Get nested value from dictionary using dot notation or list of keys
    Example: get_nested_value({'a': {'b': 'value'}}, 'a.b') returns 'value'
    """
    if isinstance(keys, str):
        keys = keys.split('.')

    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current

def chunk_list(lst, chunk_size):
    """
    Split list into chunks of specified size
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def remove_duplicates(lst, key=None):
    """
    Remove duplicates from list, optionally by key function
    """
    if not lst:
        return []

    if key is None:
        # Simple deduplication
        seen = set()
        result = []
        for item in lst:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
    else:
        # Deduplication by key
        seen = set()
        result = []
        for item in lst:
            item_key = key(item)
            if item_key not in seen:
                seen.add(item_key)
                result.append(item)
        return result

def is_valid_email(email):
    """
    Basic email validation
    """
    if not email or not isinstance(email, str):
        return False

    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_cache_key(*args):
    """
    Generate cache key from arguments
    """
    import hashlib

    key_parts = []
    for arg in args:
        if isinstance(arg, (dict, list, tuple)):
            key_parts.append(str(sorted(arg) if isinstance(arg, dict) else arg))
        else:
            key_parts.append(str(arg))

    combined = '_'.join(key_parts)
    return hashlib.md5(combined.encode()).hexdigest()

def flatten_dict(d, parent_key='', sep='_'):
    """
    Flatten nested dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)