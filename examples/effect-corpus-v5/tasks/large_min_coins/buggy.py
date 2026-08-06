def min_coins(amount, coins):
    if amount == 0:
        return 0
    return min(1 + min_coins(amount - coin, coins) for coin in coins if coin < amount)
