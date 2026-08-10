def transfer(source, destination, sku, amount):
    source.remove(sku, amount)
    destination.add(sku, amount)
    return "moved"
