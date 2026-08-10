class Clock:
    def __init__(self):
        self.time = 0

    def now(self):
        return self.time

    def advance(self, seconds):
        self.time += seconds
