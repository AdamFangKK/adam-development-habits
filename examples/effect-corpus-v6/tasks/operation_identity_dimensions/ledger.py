class Ledger:
    def __init__(self):
        self.records = {}

    def key(self, operation):
        return operation["event_id"]

    def find(self, operation):
        return self.records.get(self.key(operation))

    def save(self, operation, result):
        self.records[self.key(operation)] = result
