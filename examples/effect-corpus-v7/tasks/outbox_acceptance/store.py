class Store:
    def __init__(self):
        self.events = []

    def append(self, event):
        self.events.append(dict(event))
