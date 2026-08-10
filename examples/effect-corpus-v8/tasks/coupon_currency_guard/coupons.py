COUPONS = {"SAVE10": {"amount": 10, "currency": "USD"}}

def discount_for(code, currency):
    return COUPONS[code]["amount"]
