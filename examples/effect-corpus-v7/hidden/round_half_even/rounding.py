from decimal import Decimal, ROUND_HALF_EVEN

def cents(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))
