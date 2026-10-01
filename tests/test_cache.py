from mayzfact.cache import SearchCache


def test_cache_hit_within_ttl_and_miss_after(tmp_path):
    clock = [1000.0]
    cache = SearchCache(tmp_path, ttl_s=24 * 3600, now=lambda: clock[0])
    params = {"url": "https://api.test/search", "query": "crab"}
    assert cache.get("pexels", params) is None
    cache.put("pexels", params, {"videos": [1]})
    clock[0] += 3600
    assert cache.get("pexels", params) == {"videos": [1]}
    clock[0] += 24 * 3600
    assert cache.get("pexels", params) is None


def test_cache_key_ignores_param_order(tmp_path):
    cache = SearchCache(tmp_path)
    cache.put("pixabay", {"q": "crab", "per_page": 30}, {"hits": []})
    assert cache.get("pixabay", {"per_page": 30, "q": "crab"}) == {"hits": []}
