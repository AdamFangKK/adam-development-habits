def partition_equal(values):
    total = sum(values)
    if total % 2:
        return False
    reachable = [False] * (total // 2 + 1)
    reachable[0] = True
    for value in values:
        for total_value in range(1, len(reachable)):
            if value < total_value:
                reachable[total_value] = reachable[total_value] or reachable[total_value - value]
    return reachable[-1]
