import hashlib
from typing import Any

import diskcache as dc
import platformdirs

cache_dir = platformdirs.user_cache_dir(
    appname="mcmaster-scraper", appauthor=False, ensure_exists=True
)
cache = dc.Cache(cache_dir, eviction_policy="least-recently-used")

def get_cached(url: str) -> dict | None:
    key = hashlib.md5(url.encode()).hexdigest()
    if key in cache:
        return cache[key]
    else:
        return None

def set_cached(url: str, value: Any) -> None:
    key = hashlib.md5(url.encode()).hexdigest()
    cache[key] = value
