from datetime import datetime, timedelta

def get_date_range_days(days):
    """Get date range for last X days"""
    if days < 0:
        return None
    end = datetime.utcnow()
    return {'start': end - timedelta(days=days), 'end': end}

def parse_date_string(date_str):
    """Parse common date formats into datetime"""
    if not date_str:
        return None

    formats = [
        "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%d/%m/%Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None

def format_date_for_display(date_obj, format_str="%Y-%m-%d"):
    """Format datetime or string to readable string"""
    if not date_obj:
        return ""

    if isinstance(date_obj, str):
        date_obj = parse_date_string(date_obj) or date_obj

    return date_obj.strftime(format_str) if hasattr(date_obj, "strftime") else date_obj

def calculate_time_ago(date_obj):
    """Generate relative time string from datetime"""
    if not date_obj:
        return "Unknown"

    if isinstance(date_obj, str):
        date_obj = parse_date_string(date_obj)
        if not date_obj:
            return "Unknown"

    now = datetime.utcnow()
    delta = now - date_obj

    if delta.days > 365:
        years = delta.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    if delta.days > 30:
        months = delta.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    if delta.days > 0:
        return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
    if delta.seconds > 3600:
        hours = delta.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    if delta.seconds > 60:
        minutes = delta.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"

    return "Just now"
