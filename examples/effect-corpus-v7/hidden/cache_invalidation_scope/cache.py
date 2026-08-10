class Cache:
    def __init__(self):
        self.values = {}

    def put(self, tenant, entity, value):
        self.values[(tenant, entity)] = value

    def invalidate(self, tenant, entity):
        self.values.pop((tenant, entity), None)

    def get(self, tenant, entity):
        return self.values.get((tenant, entity))
