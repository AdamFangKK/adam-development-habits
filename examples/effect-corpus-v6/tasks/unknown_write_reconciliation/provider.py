class RetryablePreAcceptance(Exception):
    pass

class Provider:
    def __init__(self, mode):
        self.mode = mode
        self.calls = 0
        self.accepted = []

    def send(self, operation):
        self.calls += 1
        if self.mode == "retryable" and self.calls == 1:
            raise RetryablePreAcceptance()
        self.accepted.append(operation["id"])
        if self.mode == "accepted-timeout" and self.calls == 1:
            raise TimeoutError()
        return "sent"

    def reconcile(self, operation):
        return "FOUND" if operation["id"] in self.accepted else "ABSENT"
