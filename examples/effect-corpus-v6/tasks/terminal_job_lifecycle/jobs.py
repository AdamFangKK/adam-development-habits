class TerminalError(Exception):
    pass

class TransientError(Exception):
    pass

class Job:
    def __init__(self, operation):
        self.operation = operation
        self.status = "pending"
        self.attempts = 0

    def process(self):
        self.attempts += 1
        try:
            return self.operation()
        except TerminalError:
            return "retry"
        except TransientError:
            return "retry"
