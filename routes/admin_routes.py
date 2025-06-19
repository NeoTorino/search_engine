from flask import Blueprint
from utils.cache_store import cache, FIELD_FETCHERS

admin = Blueprint('admin', __name__)


@admin.route('/admin/refresh-cache', methods=['POST'])
def refresh_cache():
    for field, fetch_function in FIELD_FETCHERS.items():
        cache.refresh(field, fetch_function)
    return {"status": "cache refreshed", "fields": list(FIELD_FETCHERS.keys())}
