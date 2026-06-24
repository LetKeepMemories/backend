import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache():
    """DRF's ScopedRateThrottle counters live in Django's cache, which
    otherwise persists across tests within the same run and trips
    unrelated tests once enough login/signup calls stack up."""
    cache.clear()
    yield
