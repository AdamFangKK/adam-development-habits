class Store:
    def __init__(self):
        self.revision = 0
        self.value = None

    def apply(self, revision, value):
        if revision <= self.revision:
            return False
        self.revision = revision
        self.value = value
        return True

    def read(self):
        return self.revision, self.value
