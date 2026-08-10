class Store:
    def __init__(self):
        self.revision = 0
        self.value = {}

    def publish(self, revision, value):
        if revision <= self.revision:
            return False
        self.revision = revision
        self.value = dict(value)
        return True

    def read(self):
        return self.revision, dict(self.value)
