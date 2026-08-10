class Store:
    def __init__(self):
        self.revision = 0
        self.value = None

    def apply(self, revision, value):
        self.revision = revision
        self.value = value

    def read(self):
        return self.revision, self.value
