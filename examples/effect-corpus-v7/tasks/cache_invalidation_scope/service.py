from cache import Cache

def remove(cache, tenant, entity):
    cache.invalidate(tenant, entity)
    return cache.get(tenant, entity)
