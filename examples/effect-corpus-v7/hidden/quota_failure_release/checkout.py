def purchase(quota, payment, amount):
    quota.reserve(amount)
    try:
        payment(amount)
    except Exception:
        quota.release(amount)
        return "failed"
    return "paid"
