from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")

def total(items, tax_rate):
    subtotal = sum(Decimal(str(price)) * Decimal(str(quantity)) for price, quantity in items)
    rounded_subtotal = subtotal.quantize(CENT, rounding=ROUND_HALF_UP)
    return (rounded_subtotal * (Decimal("1") + Decimal(str(tax_rate)))).quantize(CENT, rounding=ROUND_HALF_UP)
