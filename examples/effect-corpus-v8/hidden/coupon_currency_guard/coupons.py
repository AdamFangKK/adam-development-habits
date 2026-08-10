COUPONS = {"SAVE10": {"amount": 10, "currency": "USD"}}

def discount_for(code, currency):
    coupon = COUPONS[code]
    if coupon["currency"] != currency:
        raise ValueError("coupon currency mismatch")
    return coupon["amount"]
