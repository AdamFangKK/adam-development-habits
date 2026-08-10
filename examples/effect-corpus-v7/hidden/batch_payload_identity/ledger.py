import hashlib

class Ledger:
    def __init__(self):
        self.records = {}

    def key(self, event):
        payload = event["payload"].encode("utf-8")
        return (event["event_id"], hashlib.sha256(payload).hexdigest())

    def find(self, event):
        return self.records.get(self.key(event))

    def save(self, event, result):
        self.records[self.key(event)] = result
