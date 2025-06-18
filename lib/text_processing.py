import re

def clean_text(text, remove_extra_spaces=True):
    """Clean and normalise text"""
    if not text:
        return ""

    if remove_extra_spaces:
        text = ' '.join(text.split())

    return text.strip()

def extract_domain_from_url(url):
    """Extract domain from full URL"""
    if not url:
        return ""

    if url.startswith(('http://', 'https://')):
        url = url.split('//', 1)[1]

    domain = url.split('/')[0]
    return domain[4:] if domain.startswith('www.') else domain

def slugify(text, max_length=50):
    """Slugify string into URL-safe text"""
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    return slug[:max_length].rstrip('-') if len(slug) > max_length else slug

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
