def subset_sum(capacity, items):
    reachable = [False] * (capacity + 1)
    reachable[0] = True
    for item in items:
        for total in range(1, capacity + 1):
            if item < total:
                reachable[total] = reachable[total] or reachable[total - item]
    return reachable[capacity]
