import time
from threading import Lock

from services.filters_service import get_country_list, get_organization_list, get_source_list

FIELD_FETCHERS = {
    "country": get_country_list,
    "organization": get_organization_list,
    "source": get_source_list
}

class Cache:
    """
    Thread-safe cache for storing values fetched by field, with TTL-based expiration.
    """
    def __init__(self, ttl_seconds=3600):  # 1 hour default
        self.ttl = ttl_seconds
        self.cache = {}
        self.last_updated = {}
        self.lock = Lock()

    def get_store_values(self, field_name, fetch_function):
        """
        Get cached values for a field, or fetch and store them if expired or missing.

        Args:
            field_name (str): The key for the cache.
            fetch_function (callable): Function to fetch fresh data if needed.

        Returns:
            Any: Cached or freshly fetched data.
        """
        with self.lock:
            now = time.time()
            if (field_name not in self.cache or
                now - self.last_updated.get(field_name, 0) > self.ttl):

                self.cache[field_name] = fetch_function()
                self.last_updated[field_name] = now

            return self.cache[field_name]

    def refresh(self, field_name, fetch_function):
        """
        Force refresh the cache for a specific field, bypassing TTL.

        Args:
            field_name (str): The key to refresh.
            fetch_function (callable): Function to fetch fresh data.
        """
        with self.lock:
            self.cache[field_name] = fetch_function()
            self.last_updated[field_name] = time.time()

cache = Cache()
