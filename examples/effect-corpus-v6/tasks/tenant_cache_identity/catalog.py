from policy import cache_key

class Catalog:
    def __init__(self, prices):
        self.prices = prices
        self.cache = {}

    def price(self, tenant, sku):
        key = cache_key(tenant, sku)
        if key not in self.cache:
            self.cache[key] = self.prices[(tenant, sku)]
        return self.cache[key]
