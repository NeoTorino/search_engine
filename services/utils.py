import bleach
from datetime import datetime, timedelta

def truncate_description(text, limit=300):
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."

def sanitize_input(value):
    return bleach.clean(value, tags=[], attributes={}, strip=True)

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
