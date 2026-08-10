from provider import RetryablePreAcceptance

class Dispatcher:
    def __init__(self, provider):
        self.provider = provider

    def deliver(self, operation):
        try:
            return self.provider.send(operation)
        except RetryablePreAcceptance:
            return self.deliver(operation)
        except TimeoutError:
            return self.deliver(operation)
