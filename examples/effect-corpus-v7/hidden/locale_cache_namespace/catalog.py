from policy import key

class Catalog:
    def __init__(self, values):
        self.values = values
        self.cache = {}

    def label(self, locale, product):
        cache_key = key(locale, product)
        if cache_key not in self.cache:
            self.cache[cache_key] = self.values[(locale, product)]
        return self.cache[cache_key]
