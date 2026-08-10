from serializer import serialize

class Ledger:
    def __init__(self):
        self.entries = []

    def append(self, entry):
        self.entries.append(dict(entry))

    def export(self):
        return serialize(self.entries)
