class Store:
    def __init__(self, value):
        self.record = {"value": value, "version": 1}

    def read(self):
        return self.record.copy()

    def update(self, value):
        self.record["value"] = value
