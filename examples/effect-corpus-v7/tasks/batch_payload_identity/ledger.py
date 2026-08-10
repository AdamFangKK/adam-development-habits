class Ledger:
    def __init__(self):
        self.records = {}

    def key(self, event):
        return event["event_id"]

    def find(self, event):
        return self.records.get(self.key(event))

    def save(self, event, result):
        self.records[self.key(event)] = result
