def knapsack(capacity, items):
    best = [0] * (capacity + 1)
    for weight, value in items:
        for current in range(1, capacity + 1):
            if weight < current:
                best[current] = max(best[current], value + best[current - weight])
    return best[capacity]
