class Inventory:
    def __init__(self, stock, capacity):
        self.stock = dict(stock)
        self.capacity = capacity

    def total(self):
        return sum(self.stock.values())

    def quantity(self, sku):
        return self.stock.get(sku, 0)

    def can_accept(self, amount):
        return self.total() + amount <= self.capacity

    def add(self, sku, amount):
        if not self.can_accept(amount):
            raise OverflowError("capacity")
        self.stock[sku] = self.quantity(sku) + amount

    def remove(self, sku, amount):
        if self.quantity(sku) < amount:
            raise ValueError("stock")
        self.stock[sku] = self.quantity(sku) - amount
