class Lock:
    def __init__(self):
        self.held = False

    def acquire(self):
        if self.held:
            raise RuntimeError("already held")
        self.held = True

    def release(self):
        self.held = False
