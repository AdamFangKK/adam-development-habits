def max_subarray(values):
    current = best = 0
    for value in values:
        current = max(0, current + value)
        best = max(best, current)
    return best
