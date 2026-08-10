def transfer(source, destination, sku, amount):
    if not destination.can_accept(amount):
        raise OverflowError("capacity")
    source.remove(sku, amount)
    destination.add(sku, amount)
    return "moved"
