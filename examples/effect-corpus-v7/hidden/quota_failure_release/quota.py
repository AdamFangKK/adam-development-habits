class Quota:
    def __init__(self, available):
        self.available = available

    def reserve(self, amount):
        if amount > self.available:
            raise ValueError("quota")
        self.available -= amount

    def release(self, amount):
        self.available += amount
