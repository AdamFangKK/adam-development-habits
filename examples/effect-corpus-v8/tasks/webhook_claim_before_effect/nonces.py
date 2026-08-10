class Nonces:
    def __init__(self):
        self.used = set()

    def seen(self, nonce):
        return nonce in self.used

    def mark(self, nonce):
        self.used.add(nonce)

    def claim(self, nonce):
        if nonce in self.used:
            return False
        self.used.add(nonce)
        return True
