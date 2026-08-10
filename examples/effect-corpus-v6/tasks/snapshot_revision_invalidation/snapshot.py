class Snapshot:
    def __init__(self, store):
        self.store = store
        self.cache = {}

    def read(self):
        record = self.store.read()
        key = "record"
        if key not in self.cache:
            self.cache[key] = record
        return self.cache[key]["value"]
