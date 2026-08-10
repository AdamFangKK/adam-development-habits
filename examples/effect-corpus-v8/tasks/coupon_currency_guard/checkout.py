from coupons import discount_for

def total(subtotal, currency, coupon=None):
    if coupon is None:
        return subtotal
    return subtotal - discount_for(coupon, currency)
