import hashlib

def truncate_description(text, limit=300):
    if not text or len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."

def merge_dicts(*dicts):
    result = {}
    for d in dicts:
        if isinstance(d, dict):
            result.update(d)
    return result

def flatten_dict(d, parent_key='', sep='_'):
    """Flatten nested dictionaries"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def chunk_list(lst, chunk_size):
    """Yield chunks from list"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def remove_duplicates(lst, key=None):
    """Deduplicate a list"""
    seen = set()
    result = []

    for item in lst:
        item_key = key(item) if key else item
        if item_key not in seen:
            seen.add(item_key)
            result.append(item)

    return result

def generate_cache_key(*args):
    """Hash a list of values to make a cache key"""
    key_parts = []
    for arg in args:
        if isinstance(arg, (dict, list, tuple)):
            key_parts.append(str(sorted(arg) if isinstance(arg, dict) else arg))
        else:
            key_parts.append(str(arg))

    combined = '_'.join(key_parts)
    return hashlib.md5(combined.encode()).hexdigest()

def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def get_nested_value(data, keys, default=None):
    if isinstance(keys, str):
        keys = keys.split('.')

    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current
