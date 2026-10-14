import time
from typing import List, Dict, Callable

from app.core.config import settings


class ProductCatalogCache:
    """In‑memory cache for the product catalog with TTL.

    The cache holds the list of product dictionaries and the timestamp of the
    last refresh.  When ``get_products`` is called, it checks whether the cached
    data is older than ``settings.CATALOG_TTL_SECONDS`` (default 900 s).  If the
    cache is stale or empty, it calls the supplied ``fetch_func`` to retrieve a
    fresh list from Firestore and updates the cache.
    """

    _products: List[Dict] = []
    _last_refresh: float = 0.0

    @classmethod
    def get_products(cls, fetch_func: Callable[[], List[Dict]]) -> List[Dict]:
        """Return cached products or refresh if TTL elapsed.

        Args:
            fetch_func: Callable that returns a fresh list of product dicts.
        """
        now = time.time()
        if not cls._products or (now - cls._last_refresh) > settings.CATALOG_TTL_SECONDS:
            cls._products = fetch_func()
            cls._last_refresh = now
        return cls._products
