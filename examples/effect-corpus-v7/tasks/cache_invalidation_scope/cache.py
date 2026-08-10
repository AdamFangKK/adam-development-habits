class Cache:
    def __init__(self):
        self.values = {}

    def put(self, tenant, entity, value):
        self.values[(tenant, entity)] = value

    def invalidate(self, tenant, entity):
        for key in list(self.values):
            if key[1] == entity:
                del self.values[key]

    def get(self, tenant, entity):
        return self.values.get((tenant, entity))
