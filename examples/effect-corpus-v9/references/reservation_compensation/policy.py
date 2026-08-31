def evaluate(stock, requested, payment_ok):
    return stock - requested if payment_ok else stock
