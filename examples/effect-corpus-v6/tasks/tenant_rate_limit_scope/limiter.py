class Limiter:
    def __init__(self, limit):
        self.limit = limit
        self.counts = {}

    def allow(self, tenant, user):
        key = user
        count = self.counts.get(key, 0)
        if count >= self.limit:
            return False
        self.counts[key] = count + 1
        return True
