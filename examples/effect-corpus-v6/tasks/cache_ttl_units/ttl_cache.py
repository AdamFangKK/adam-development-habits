class Cache:
    def __init__(self):
        self.values = {}

    def put(self, key, value, ttl_ms, now):
        self.values[key] = (value, now + ttl_ms)

    def get(self, key, now):
        entry = self.values.get(key)
        return None if entry is None or now >= entry[1] else entry[0]
