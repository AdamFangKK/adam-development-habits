class Manifest:
    def __init__(self):
        self.latest = None

    def point_to(self, key):
        self.latest = key
