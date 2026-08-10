def purchase(quota, payment, amount):
    quota.reserve(amount)
    try:
        payment(amount)
    except Exception:
        return "failed"
    return "paid"
