class Store:
    def __init__(self):
        self.revision = 0
        self.value = {}

    def publish(self, revision, value):
        self.revision = revision
        self.value = dict(value)

    def read(self):
        return self.revision, dict(self.value)
