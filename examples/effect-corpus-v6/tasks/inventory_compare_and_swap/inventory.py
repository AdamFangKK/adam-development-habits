class Store:
    def __init__(self, quantity):
        self.quantity = quantity
        self.version = 1

    def read(self):
        return self.quantity, self.version

    def compare_and_reserve(self, expected_version, amount):
        if expected_version != self.version or amount > self.quantity:
            return False
        self.quantity -= amount
        self.version += 1
        return True

class Reservation:
    def __init__(self, store):
        self.store = store

    def reserve(self, amount):
        quantity, version = self.store.read()
        if amount <= quantity:
            self.store.compare_and_reserve(version, amount)
            return True
        return False
