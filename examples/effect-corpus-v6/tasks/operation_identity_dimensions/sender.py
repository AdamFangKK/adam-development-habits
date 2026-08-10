class Sender:
    def __init__(self, ledger):
        self.ledger = ledger
        self.sent = []

    def send(self, operation):
        prior = self.ledger.find(operation)
        if prior is not None:
            return prior
        result = {"amount": operation["amount"], "tenant": operation["tenant"]}
        self.sent.append(operation.copy())
        self.ledger.save(operation, result)
        return result
