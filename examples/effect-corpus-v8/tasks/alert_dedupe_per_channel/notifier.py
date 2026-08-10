from keys import dedupe_key

class Notifier:
    def __init__(self):
        self.sent = set()
        self.deliveries = []

    def send(self, channel, event_id, message):
        key = dedupe_key(channel, event_id)
        if key in self.sent:
            return False
        self.sent.add(key)
        self.deliveries.append((channel, message))
        return True
