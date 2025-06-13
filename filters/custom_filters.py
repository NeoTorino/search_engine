from datetime import datetime
from markupsafe import escape

def format_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        days_ago = (today - date_obj).days

        if days_ago == 0:
            return "Today"
        elif days_ago == 1:
            return "Yesterday"
        elif days_ago <= 30:
            return f"{days_ago} days ago"
        return "30+ days ago"
    except Exception:
        return escape(date_str)

def register_filters(app):
    app.jinja_env.filters['format_date'] = format_date
